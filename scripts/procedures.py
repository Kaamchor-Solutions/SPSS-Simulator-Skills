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
