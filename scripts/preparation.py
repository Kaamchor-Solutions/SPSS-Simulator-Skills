"""Deterministic, opt-in derived fields; never mutate the caller's source frame."""
import numpy as np
import pandas as pd


def prepare(df, cfg):
    from analyze import require_columns, make_audit
    data = df.copy(deep=True)
    audit = []
    rules = cfg.get('rules', [])
    if not isinstance(rules, list) or not rules:
        raise ValueError('prepare requires a non-empty rules list')
    for rule in rules:
        if not isinstance(rule, dict):
            raise ValueError('Each preparation rule must be an object')
        source, target = rule.get('source'), rule.get('target')
        require_columns(data, [source])
        if not isinstance(target, str) or not target or target in data.columns:
            raise ValueError('target must be a new non-empty column name; source columns cannot be overwritten')
        s = data[source]
        mode = rule.get('kind')
        if mode in ('recode', 'range'):
            default = rule.get('unmatched', 'preserve')
            if default not in ('preserve', 'missing', 'error'):
                raise ValueError('unmatched must be preserve, missing or error')
            out = s.astype(object).copy() if default == 'preserve' else pd.Series(np.nan, index=s.index, dtype=object)
            matched = pd.Series(False, index=s.index)
            if mode == 'recode':
                entries = rule.get('values', [])
                if not entries:
                    raise ValueError('recode requires values: [{from: typed value, to: value}]')
                for entry in entries:
                    if 'from' not in entry or 'to' not in entry:
                        raise ValueError('recode entries require from and to')
                    mask = s.isna() if entry['from'] is None else s.eq(entry['from']).fillna(False)
                    if (matched & mask).any():
                        raise ValueError('Overlapping recode entries')
                    out.loc[mask] = entry['to']; matched |= mask
            else:
                numeric = pd.to_numeric(s, errors='coerce').replace([np.inf, -np.inf], np.nan)
                entries = rule.get('ranges', [])
                if not entries:
                    raise ValueError('range requires ranges: [{min: number, max: number, to: value}]')
                for entry in entries:
                    lo, hi = entry.get('min', -np.inf), entry.get('max', np.inf)
                    if not isinstance(lo, (int,float)) or not isinstance(hi, (int,float)) or lo >= hi or 'to' not in entry:
                        raise ValueError('Range bounds must be numeric and increasing; to is required')
                    mask = numeric.ge(lo) & numeric.lt(hi)  # left closed, right open
                    if (matched & mask).any():
                        raise ValueError('Overlapping range entries')
                    out.loc[mask] = entry['to']; matched |= mask
            if default == 'error' and (s.notna() & ~matched).any():
                raise ValueError(f'Unmatched nonmissing values in {source!r}')
            data[target] = out
            audit.append(dict(kind=mode, source=source, target=target, matched=int(matched.sum()),
                              unmatched_nonmissing=int((s.notna() & ~matched).sum()),
                              missing_before=int(s.isna().sum()), missing_after=int(out.isna().sum()), rule=rule))
        elif mode == 'dummy':
            levels, reference = rule.get('levels'), rule.get('reference')
            if not isinstance(levels,list) or len(levels)<2 or len(set(levels)) != len(levels) or reference not in levels:
                raise ValueError('dummy requires distinct ordered levels and an explicit reference level')
            if (s.notna() & ~s.isin(levels)).any():
                raise ValueError('Observed category outside declared dummy levels')
            names=[]
            for i, level in enumerate(levels):
                if level == reference:
                    continue
                name = f'{target}_{i}'
                if name in data.columns:
                    raise ValueError('Dummy column collision')
                data[name] = s.eq(level).astype(float).where(s.notna(), np.nan)
                names.append(dict(column=name, level=level))
            audit.append(dict(kind=mode,source=source,reference=reference,columns=names,rule=rule))
        else:
            raise ValueError('Rule kind must be recode, range or dummy')
    return data, audit


def prepare_result(df,cfg):
    from analyze import make_audit
    data, audit = prepare(df,cfg)
    return dict(action='prepare', columns=list(data.columns), records=data.to_dict(orient='records'),
                transformations=audit, source_preserved=True, data_audit=make_audit(len(df),len(data),[]),
                note='Derived columns only; range intervals are [min,max). No filters or imputations. Records can contain sensitive values: do not share without review.')
