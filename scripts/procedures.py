"""Additional procedures: computed library results, never synthetic inference."""
import numpy as np
import pandas as pd
from scipy import stats


def grouped(df,cfg,min_n=2):
    from analyze import require_columns, numeric_series_audit, make_audit
    outcome, group = cfg.get('outcome'),cfg.get('group')
    require_columns(df,[outcome,group])
    y, exclusions = numeric_series_audit(df,outcome)
    labels=cfg.get('groups',list(pd.unique(df[group].dropna())))
    if len(labels)<2 or len(set(labels)) != len(labels):
        raise ValueError('Requires at least two distinct group labels')
    values=[]
    for label in labels:
        x=y.loc[df[group].eq(label)].dropna().to_numpy(dtype=float)
        if len(x)<min_n:
            raise ValueError(f'Group {label!r} needs at least {min_n} usable values; observed {list(pd.unique(df[group].dropna()))!r}')
        values.append(x)
    n=sum(map(len,values))
    audit=make_audit(len(df),n,exclusions+([dict(reason='row dropped: outside selected groups or incomplete',count=len(df)-n)] if n<len(df) else []))
    return labels, values, audit


def levene(df,cfg):
    from analyze import invalid_result
    labels,values,audit=grouped(df,cfg)
    with np.errstate(divide='ignore',invalid='ignore'):
        r=stats.levene(*values,center='mean')
    fields=dict(groups=labels,n=sum(map(len,values)),df1=len(values)-1,df2=sum(map(len,values))-len(values),center='mean',data_audit=audit)
    if not np.isfinite(r.statistic) or not np.isfinite(r.pvalue):
        return invalid_result('levene','Absolute deviations have no residual variance',**fields)
    return dict(action='levene',F=r.statistic,p=r.pvalue,**fields)


def nonparametric(df,cfg):
    from analyze import require_columns, numeric_series_audit, make_audit, invalid_result
    action=cfg['action']
    if action=='wilcoxon':
        outcome, first=cfg.get('outcome'),cfg.get('paired_with')
        require_columns(df,[outcome,first])
        y,ey=numeric_series_audit(df,outcome);x,ex=numeric_series_audit(df,first)
        pair=pd.concat([x,y],axis=1).dropna()
        if len(pair)<2:
            raise ValueError('Wilcoxon requires two complete pairs')
        d=pair.iloc[:,1].to_numpy()-pair.iloc[:,0].to_numpy()
        # Optional rounding must reflect measurement precision, never hide ties.
        decimals=cfg.get('difference_decimals')
        if decimals is not None:
            if not isinstance(decimals,int) or not 0<=decimals<=12:
                raise ValueError('difference_decimals must be an integer 0..12')
            d=np.round(d,decimals)
        zero=cfg.get('zero_method','wilcox')
        if zero not in ('wilcox','pratt','zsplit'):
            raise ValueError('zero_method must be wilcox, pratt or zsplit')
        method=cfg.get('method','asymptotic')
        if method not in ('exact','asymptotic'):
            raise ValueError('method must be exact or asymptotic')
        audit=make_audit(len(df),len(pair),ex+ey+([dict(reason='row dropped: incomplete pair',count=len(df)-len(pair))] if len(pair)<len(df) else []))
        if np.all(d==0):
            return invalid_result(action,'All paired differences are zero; inference not reported',n=len(d),data_audit=audit)
        if method=='exact' and (np.any(d==0) or len(np.unique(np.abs(d)))<len(d)):
            raise ValueError('Exact Wilcoxon requires no zeros and no tied absolute differences; select asymptotic explicitly')
        r=stats.wilcoxon(d,zero_method=zero,correction=True,alternative='two-sided',method=method)
        return dict(action=action,n=len(d),statistic=r.statistic,p=r.pvalue,method=method,zero_method=zero,continuity_correction=True,
                    difference_direction='outcome minus paired_with',difference_decimals=decimals,zero_count=int((d==0).sum()),
                    data_audit=audit,note='Signed-rank inference assumes symmetric independent paired differences. Zeros handled by the declared policy; asymptotic default avoids implicit exact fallback.')
    labels,values,audit=grouped(df,cfg,min_n=1)
    if action=='mann_whitney':
        if len(values)!=2:
            raise ValueError('Mann-Whitney requires exactly two groups')
        method=cfg.get('method','asymptotic')
        if method not in ('exact','asymptotic'):
            raise ValueError('method must be exact or asymptotic')
        allvals=np.concatenate(values)
        if method=='exact' and len(np.unique(allvals))<len(allvals):
            raise ValueError('Exact Mann-Whitney requires no ties; select asymptotic explicitly')
        r=stats.mannwhitneyu(*values,alternative='two-sided',method=method,use_continuity=True)
        return dict(action=action,groups=labels,group_n=list(map(len,values)),n=len(allvals),statistic=r.statistic,p=r.pvalue,
                    method=method,continuity_correction=True,data_audit=audit,
                    note='U corresponds to the first selected group; two-sided p. Rank test of distributions, not automatically a median test. Asymptotic inference uses tie correction.')
    if action=='kruskal_wallis':
        if len(np.unique(np.concatenate(values)))<2:
            return invalid_result(action,'All values identical; rank variance is zero',data_audit=audit)
        r=stats.kruskal(*values)
        return dict(action=action,groups=labels,group_n=list(map(len,values)),n=sum(map(len,values)),statistic=r.statistic,p=r.pvalue,df=len(values)-1,
                    method='asymptotic chi-square, tie-corrected',data_audit=audit,
                    note='Independent groups. Small groups can make chi-square inference unreliable; no pairwise rank post hoc tests.')
    raise ValueError('Unknown rank procedure')


def fisher(df,cfg):
    from analyze import require_columns, make_audit
    row,col=cfg.get('row'),cfg.get('column');require_columns(df,[row,col])
    pair=df[[row,col]].dropna();tab=pd.crosstab(pair[row],pair[col])
    if tab.shape!=(2,2):
        raise ValueError('Fisher exact requires exactly two observed levels per variable (2x2)')
    r=stats.fisher_exact(tab.to_numpy(),alternative='two-sided')
    return dict(action='fisher_exact',n=len(pair),row_levels=list(tab.index),column_levels=list(tab.columns),counts=tab.to_numpy().tolist(),
                odds_ratio=r.statistic,p=r.pvalue,method='two-sided probability-ordering exact',data_audit=make_audit(len(df),len(pair),[dict(reason='row dropped: incomplete pair',count=len(df)-len(pair))]),
                note='Conditional 2x2 exact test with fixed margins; sample odds ratio can be infinite. Not a conditional-MLE odds-ratio CI.')


def welch_anova(df,cfg):
    from statsmodels.stats.oneway import anova_oneway
    from analyze import invalid_result
    labels,values,audit=grouped(df,cfg)
    if any(np.var(v,ddof=1)==0 for v in values):
        return invalid_result('welch_anova','Welch ANOVA requires positive variance in every group',data_audit=audit)
    r=anova_oneway(values,use_var='unequal',welch_correction=True)
    return dict(action='welch_anova',groups=labels,n=sum(map(len,values)),F=r.statistic,p=r.pvalue,df1=r.df_num,df2=r.df_denom,data_audit=audit,
                note='Welch-Satterthwaite approximate F; no pooled variance and no automatic post hoc selection.')


def posthoc(df,cfg):
    from statsmodels.stats.multicomp import pairwise_tukeyhsd
    from analyze import invalid_result
    labels,values,audit=grouped(df,cfg)
    unequal=cfg['action']=='games_howell'
    if unequal and any(np.var(v,ddof=1)==0 for v in values):
        return invalid_result('games_howell','Games-Howell requires positive group variances',data_audit=audit)
    if not unequal and sum((len(v)-1)*np.var(v,ddof=1) for v in values)==0:
        return invalid_result('tukey','Tukey requires positive pooled residual variance',data_audit=audit)
    # Integer IDs avoid sorting/mixed-label ambiguity. statsmodels owns all tests/CIs.
    ids=np.concatenate([np.repeat(i,len(v)) for i,v in enumerate(values)])
    r=pairwise_tukeyhsd(np.concatenate(values),ids,alpha=.05,use_var='unequal' if unequal else 'equal')
    pairs=[]
    for m,(i,j) in enumerate(zip(*r._multicomp.pairindices)):
        pairs.append(dict(first=labels[i],second=labels[j],difference_second_minus_first=r.meandiffs[m],p_adjusted=r.pvalues[m],
                          ci95=list(r.confint[m]),reject_05=bool(r.reject[m])))
    return dict(action=cfg['action'],groups=labels,n=sum(map(len,values)),comparisons=pairs,data_audit=audit,
                note='Familywise 95% pairwise intervals from statsmodels; difference is second minus first. '+('Games-Howell uses unequal variances and pair-specific Welch df.' if unequal else 'Tukey-Kramer uses pooled residual variance for unequal sample sizes.'))
