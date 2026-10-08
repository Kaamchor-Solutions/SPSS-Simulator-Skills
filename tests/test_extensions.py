import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import numpy as np
import pandas as pd
import pytest
from scipy import stats
import statsmodels.api as sm
import analyze
import spss_report


def run(df, **cfg):
    return analyze.run_request(dict(file='fixture.csv', **cfg), df)

@pytest.mark.parametrize('labels', [['1','2'], [1,2]])
def test_typed_groups(labels):
    observed=[1,1,2,2] if isinstance(labels[0],str) else ['1','1','2','2']
    with pytest.raises(ValueError, match='observed values/types'):
        run(pd.DataFrame(dict(g=observed,y=[1,2,3,5])), action='ttest',outcome='y',group='g',groups=labels)

def test_paired_syntax_sign():
    cfg=dict(action='ttest',outcome='after',paired_with='before')
    assert 'PAIRS=after WITH before' in spss_report.spss_syntax(cfg,{})

def test_singleton_retained():
    df=pd.DataFrame(dict(g=['a','a','b','b','c'],y=[1,2,3,4,10]))
    r=run(df,action='anova',outcome='y',group='g',singleton_policy='retain')
    assert r['n']==5 and r['df_between']==2
    assert r['F']==pytest.approx(49) and r['p']==pytest.approx(.02)
    with pytest.raises(ValueError,match='Singleton'):
        run(df,action='anova',outcome='y',group='g',singleton_policy='error')

def test_percentile_method():
    r=run(pd.DataFrame(dict(x=[0,1,2,5,9,13])),action='describe',variables=['x'])
    assert r['variables'][0]['q1']==1.25
    assert 'type 7' in r['variables'][0]['percentile_estimator']

def test_noisy_unequal_t():
    a=np.array([1,2,8,4,5]); b=np.array([6,4,9,5,7,2,12])
    r=run(pd.DataFrame(dict(g=['a']*5+['b']*7,y=np.r_[a,b])),action='ttest',group='g',outcome='y')
    ref=stats.ttest_ind(a,b,equal_var=False)
    assert r['t']==pytest.approx(ref.statistic) and r['p_two_sided']==pytest.approx(ref.pvalue)

@pytest.mark.parametrize('model',['linear','logistic'])
def test_noisy_multi_predictor_exact(model):
    rng=np.random.default_rng(765)
    x=rng.normal(size=(140,2)); eta=.3+.4*x[:,0]-.6*x[:,1]
    y=eta+rng.normal(size=140) if model=='linear' else rng.binomial(1,1/(1+np.exp(-eta)))
    df=pd.DataFrame(dict(y=y,x=x[:,0],z=x[:,1])); X=sm.add_constant(df[['x','z']])
    ref=sm.OLS(y,X).fit() if model=='linear' else sm.Logit(y,X).fit(disp=False)
    r=run(df,action='regression',model=model,outcome='y',predictors=['x','z'])
    for name in X:
        term=r['terms'][name]
        assert term['B' if model=='linear' else 'B_log_odds']==pytest.approx(ref.params[name],abs=1e-10)
        assert term['SE']==pytest.approx(ref.bse[name],abs=1e-10)
        assert term['CI95' if model=='linear' else 'CI95_B']==pytest.approx(ref.conf_int().loc[name].tolist(),abs=1e-10)
