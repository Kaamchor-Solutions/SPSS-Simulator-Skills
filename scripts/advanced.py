"""Restricted advanced models with explicit design and estimand settings."""
import numpy as np
import pandas as pd


def factorial(df,cfg):
    import statsmodels.formula.api as smf
    from statsmodels.stats.anova import anova_lm
    from analyze import require_columns,numeric_series_audit,make_audit,invalid_result
    outcome=cfg.get('outcome');factors=cfg.get('factors',[]);covariates=cfg.get('covariates',[])
    if cfg['action']=='anova_two_way' and len(factors)!=2:
        raise ValueError('Two-way ANOVA requires exactly two factors')
    if cfg['action']=='ancova' and (not factors or not covariates):
        raise ValueError('ANCOVA requires factors and covariates')
    names=[outcome]+factors+covariates
    if len(set(names))!=len(names):
        raise ValueError('Outcome, factors and covariates must be distinct')
    require_columns(df,names)
    ss=cfg.get('ss_type',3)
    if ss not in (2,3):
        raise ValueError('ss_type must be 2 or 3')
    # Internal aliases prevent formula injection through source variable names.
    data=pd.DataFrame(index=df.index);exclusions=[]
    y,ey=numeric_series_audit(df,outcome);data['y']=y;exclusions+=ey
    for i,c in enumerate(covariates):
        x,e=numeric_series_audit(df,c);data[f'x{i}']=x;exclusions+=e
    for i,f in enumerate(factors):
        data[f'f{i}']=df[f]
    data=data.dropna();n=len(data)
    audit=make_audit(len(df),n,exclusions+([dict(reason='row dropped: incomplete model',count=len(df)-n)] if n<len(df) else []))
    if n==0:
        raise ValueError('No complete model observations')
    levels=[list(pd.unique(data[f'f{i}'])) for i in range(len(factors))]
    if any(len(l)<2 for l in levels):
        raise ValueError('Each factor requires at least two observed levels')
    contrast=cfg.get('contrast','sum')
    if contrast!='sum':
        raise ValueError('Only sum-to-zero contrasts supported; treatment contrasts change Type III tests')
    interaction=cfg.get('interaction',cfg['action']=='anova_two_way')
    if not isinstance(interaction,bool):
        raise ValueError('interaction must be boolean')
    fs=[f'C(f{i}, Sum)' for i in range(len(factors))]
    formula='y ~ '+ (' * '.join(fs) if interaction else ' + '.join(fs))
    if covariates:
        formula+=' + '+' + '.join(f'x{i}' for i in range(len(covariates)))
    # ANCOVA tests a common-slope model, not a test of slope homogeneity.
    fit=smf.ols(formula,data=data).fit()
    if np.linalg.matrix_rank(fit.model.exog)<fit.model.exog.shape[1] or fit.df_resid<=0 or fit.ssr<=np.finfo(float).eps:
        return invalid_result(cfg['action'],'Rank-deficient design, no residual df or zero residual variance',n=n,data_audit=audit)
    table=anova_lm(fit,typ=ss)
    rows=[]
    rename={f'C(f{i}, Sum)':f for i,f in enumerate(factors)}|{f'x{i}':c for i,c in enumerate(covariates)}
    for term,row in table.iterrows():
        label=term
        for alias,name in rename.items(): label=label.replace(alias,name)
        rows.append(dict(term=label,sum_sq=row['sum_sq'],df=row['df'],F=row.get('F'),p=row.get('PR(>F)')))
    return dict(action=cfg['action'],outcome=outcome,factors=factors,covariates=covariates,n=n,ss_type=ss,contrast=contrast,
                interaction=interaction,formula=formula,terms=rows,residual_df=fit.df_resid,R_squared=fit.rsquared,data_audit=audit,
                note='OLS Type '+str(ss)+' sums of squares, sum-to-zero contrasts, listwise complete cases. '+
                ('ANCOVA uses additive common slopes; verify slope homogeneity and covariate overlap separately. ' if covariates else '')+
                'Unbalanced main effects depend on SS policy. Empty/aliased cells fail; no marginal-means or causal inference.')


def repeated(df,cfg):
    import pingouin as pg
    from analyze import require_columns,numeric_series_audit,make_audit,invalid_result
    subject,within,outcome=cfg.get('subject'),cfg.get('within'),cfg.get('outcome')
    if not all(isinstance(x,str) and x for x in (subject,within,outcome)) or len(set([subject,within,outcome]))!=3:
        raise ValueError('Repeated ANOVA requires distinct subject, within and outcome columns (long format)')
    require_columns(df,[subject,within,outcome])
    y,exclusions=numeric_series_audit(df,outcome)
    data=pd.DataFrame(dict(subject=df[subject],within=df[within],y=y)).dropna(subset=['subject','within'])
    if data.duplicated(['subject','within']).any():
        raise ValueError('Duplicate subject/condition cells; do not silently aggregate')
    levels=list(pd.unique(data.within))
    if len(levels)<2:
        raise ValueError('At least two within-subject levels required')
    wide=data.pivot(index='subject',columns='within',values='y').reindex(columns=levels)
    complete=wide.dropna()
    if len(complete)<3:
        raise ValueError('At least three complete subjects required')
    long=complete.reset_index().melt(id_vars='subject',var_name='within',value_name='y')
    used=len(long);audit=make_audit(len(df),used,exclusions+([dict(reason='row dropped: incomplete subject or missing identity/condition',count=len(df)-used)] if used<len(df) else []))
    # Avoid presenting nonfinite Mauchly/GG diagnostics as passed.
    with np.errstate(divide='ignore',invalid='ignore'):
        table=pg.rm_anova(data=long,dv='y',within='within',subject='subject',correction=True,detailed=True)
        sph=pg.sphericity(complete); eps_gg=pg.epsilon(complete,correction='gg');eps_hf=pg.epsilon(complete,correction='hf')
    spherical, sph_w, sph_chi, sph_df, sph_p = sph
    row=table.iloc[0];F=row['F'];df1=row['DF'];df2=table.iloc[1]['DF']
    if not np.isfinite(F) or not np.isfinite(row['p_unc']):
        return invalid_result('anova_repeated','Repeated-model inference nonfinite (degenerate covariance/residual variance)',data_audit=audit)
    from scipy import stats
    corrections={}
    for name,eps in [('greenhouse_geisser',eps_gg),('huynh_feldt',eps_hf)]:
        corrections[name]=dict(epsilon=eps,df1=df1*eps,df2=df2*eps,p=stats.f.sf(F,df1*eps,df2*eps),valid=bool(np.isfinite(eps) and eps>0))
    return dict(action='anova_repeated',n_subjects=len(complete),n=used,levels=levels,F=F,df1=df1,df2=df2,p=row['p_unc'],
                generalized_eta_squared=row['ng2'],sphericity=dict(W=sph_w,chi_square=sph_chi,df=sph_df,p=sph_p,
                valid=bool(np.isfinite(sph_w) and np.isfinite(sph_p)),spherical=bool(spherical)),corrections=corrections,data_audit=audit,
                note='One within-subject factor only; complete-subject deletion, no mixed/between-subject factors. GG/HF corrected dfs and p from package epsilon and scipy F survival. For two levels sphericity is automatic; inspect covariance degeneracy for more levels. No multivariate follow-up.')


def pca(df,cfg):
    from sklearn.decomposition import PCA
    from statsmodels.multivariate.factor_rotation import rotate_factors
    from analyze import require_columns,numeric_series_audit,make_audit
    variables=cfg.get('variables',[]);require_columns(df,variables)
    if len(variables)<2:
        raise ValueError('PCA requires at least two distinct scale variables')
    numeric={};exclusions=[]
    for v in variables:
        x,e=numeric_series_audit(df,v);numeric[v]=x;exclusions+=e
    data=pd.DataFrame(numeric).dropna()
    if len(data)<3 or (data.std(ddof=1)==0).any():
        raise ValueError('PCA requires at least three complete rows and nonconstant columns')
    scale=cfg.get('scale','correlation')
    if scale not in ('correlation','covariance'):
        raise ValueError('scale must be correlation or covariance')
    rotation=cfg.get('rotation','none')
    if rotation not in ('none','varimax'):
        raise ValueError('rotation must be none or varimax')
    k=cfg.get('n_components',len(variables))
    if not isinstance(k,int) or isinstance(k,bool) or not 1<=k<=min(len(data)-1,len(variables)):
        raise ValueError('n_components must be 1..min(N-1,number of variables)')
    centered=data-data.mean()
    if scale=='correlation': centered=centered/data.std(ddof=1)
    fit=PCA(n_components=k,svd_solver='full').fit(centered)
    loadings=fit.components_.T*np.sqrt(fit.explained_variance_)
    transform=np.eye(k)
    if rotation=='varimax':
        if k<2:
            raise ValueError('Varimax needs at least two retained components')
        loadings,transform=rotate_factors(loadings,'varimax')
    # Stable sign display only; signs are mathematically arbitrary.
    signs=np.array([1 if loadings[np.argmax(np.abs(loadings[:,j])),j]>=0 else -1 for j in range(k)])
    loadings*=signs;transform*=signs
    used=len(data)
    return dict(action='pca',variables=variables,n=used,scale=scale,rotation=rotation,n_components=k,
                eigenvalues=fit.explained_variance_.tolist(),explained_variance_ratio=fit.explained_variance_ratio_.tolist(),
                loadings=loadings.tolist(),rotation_matrix=transform.tolist(),communalities=np.sum(loadings**2,axis=1).tolist(),
                data_audit=make_audit(len(df),used,exclusions+([dict(reason='row dropped: incomplete across PCA variables',count=len(df)-used)] if used<len(df) else [])),
                note='Principal components extraction, not common factor analysis. Correlation mode uses sample-SD scaling; full SVD. Varimax is orthogonal without Kaiser normalization. Eigenvalues/variance ratios are pre-rotation. Largest absolute loading positive for display; sign changes do not alter the solution. No scores, KMO/Bartlett or automatic retention rule.')
