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

@pytest.mark.parametrize('constant',[False,True])
def test_levene(constant):
    df=pd.DataFrame(dict(g=['a']*4+['b']*5,y=[1]*9 if constant else [1,2,5,9,2,3,6,12,17]))
    r=run(df,action='levene',outcome='y',group='g')
    if constant:
        assert r['valid'] is False
    else:
        ref=stats.levene(df.y[:4],df.y[4:],center='mean')
        assert r['F']==pytest.approx(ref.statistic) and r['p']==pytest.approx(ref.pvalue)
        assert r['df2']==7

def test_pooled_t_and_zero_diff_se():
    import spss_format
    df=pd.DataFrame(dict(g=['a']*3+['b']*4,y=[1,2,3,0,1,3,4]))
    r=run(df,action='ttest',outcome='y',group='g')
    ref=stats.ttest_ind(df.y[:3],df.y[3:],equal_var=True)
    assert r['pooled_variance']['t']==pytest.approx(ref.statistic)
    assert r['standard_error_welch']>0
    text=spss_format.format_result(r)
    assert 'Equal variances assumed' in text and "Levene's Test" in text

@pytest.mark.parametrize('rule',[
    dict(kind='recode',source='x',target='x',values=[{'from':1,'to':2}]),
    dict(kind='range',source='x',target='z',ranges=[dict(min=0,max=5,to=1),dict(min=1,max=8,to=2)]),
    dict(kind='dummy',source='g',target='z',levels=['a','c'],reference='a'),
    dict(kind='recode',source='g',target='z',values=[{'from':'a','to':0}],unmatched='error'),
])
def test_prepare_invalid(rule):
    with pytest.raises(ValueError):
        run(pd.DataFrame(dict(x=[1,3],g=['a','b'])),action='prepare',rules=[rule])

def test_prepare_preserves_source():
    df=pd.DataFrame(dict(x=[1,3,7,None],g=['a','b','b',None])); original=df.copy()
    r=run(df,action='prepare',rules=[dict(kind='range',source='x',target='band',ranges=[dict(min=0,max=3,to=0),dict(min=3,max=8,to=1)],unmatched='missing'),dict(kind='dummy',source='g',target='d',levels=['a','b'],reference='a')])
    pd.testing.assert_frame_equal(df,original)
    assert [a['band'] for a in r['records']]==[0,1,1,None]
    assert [a['d_1'] for a in r['records']]==[0,1,1,None]
    assert r['transformations'][0]['matched']==3

def test_recode_typed():
    r=run(pd.DataFrame(dict(x=[1,'1',None])),action='prepare',rules=[dict(kind='recode',source='x',target='z',values=[{'from':1,'to':'numeric'},{'from':'1','to':'text'}])])
    assert [a['z'] for a in r['records']]==['numeric','text',None]

@pytest.fixture
def rank_data():
    return pd.DataFrame(dict(g=['a']*4+['b']*5+['c']*3,y=[1,2,2,5,2,4,7,9,11,3,6,8]))

@pytest.mark.parametrize('action',['mann_whitney','kruskal_wallis','welch_anova','tukey','games_howell'])
def test_phase2_library_agreement(rank_data,action):
    import spss_format
    groups=['a','b'] if action=='mann_whitney' else ['a','b','c']
    vals=[rank_data.y[rank_data.g==g].to_numpy() for g in groups]
    r=run(rank_data,action=action,outcome='y',group='g',groups=groups)
    if action=='mann_whitney':
        ref=stats.mannwhitneyu(*vals,method='asymptotic',use_continuity=True)
        assert r['statistic']==pytest.approx(ref.statistic);assert r['p']==pytest.approx(ref.pvalue)
    elif action=='kruskal_wallis':
        ref=stats.kruskal(*vals);assert r['statistic']==pytest.approx(ref.statistic);assert r['p']==pytest.approx(ref.pvalue)
    elif action=='welch_anova':
        from statsmodels.stats.oneway import anova_oneway
        ref=anova_oneway(vals,use_var='unequal',welch_correction=True)
        assert r['F']==pytest.approx(ref.statistic);assert r['df2']==pytest.approx(ref.df_denom)
    else:
        from statsmodels.stats.multicomp import pairwise_tukeyhsd
        ref=pairwise_tukeyhsd(rank_data.y,rank_data.g,use_var='equal' if action=='tukey' else 'unequal')
        assert [p['p_adjusted'] for p in r['comparisons']]==pytest.approx(ref.pvalues)
        assert np.array([p['ci95'] for p in r['comparisons']])==pytest.approx(ref.confint)
    assert spss_format.format_result(r,style='markdown')
    assert spss_report.interpret(r)

@pytest.mark.parametrize('action',['mann_whitney','wilcoxon'])
def test_exact_ties_rejected(action,rank_data):
    with pytest.raises(ValueError,match='Exact'):
        if action=='mann_whitney':
            run(rank_data,action=action,outcome='y',group='g',groups=['a','b'],method='exact')
        else:
            run(pd.DataFrame(dict(before=[1,2,3,4],after=[2,3,3,6])),action=action,outcome='after',paired_with='before',method='exact')

@pytest.mark.parametrize('zero',['wilcox','pratt','zsplit'])
def test_wilcoxon_zeros(zero):
    d=np.array([0,1,2,2,-3,4,-1,0])
    df=pd.DataFrame(dict(before=np.arange(8),after=np.arange(8)+d))
    r=run(df,action='wilcoxon',outcome='after',paired_with='before',zero_method=zero)
    ref=stats.wilcoxon(d,zero_method=zero,method='asymptotic',correction=True)
    assert r['p']==pytest.approx(ref.pvalue) and r['statistic']==pytest.approx(ref.statistic)
    assert r['zero_count']==2

@pytest.mark.parametrize('action',['mann_whitney','wilcoxon'])
def test_exact_untied(action):
    if action=='mann_whitney':
        df=pd.DataFrame(dict(g=['a']*3+['b']*3,y=[1,2,7,3,4,8]))
        r=run(df,action=action,outcome='y',group='g',method='exact')
        ref=stats.mannwhitneyu([1,2,7],[3,4,8],method='exact')
    else:
        df=pd.DataFrame(dict(before=[0]*5,after=[1,-2,3,4,-5]))
        r=run(df,action=action,outcome='after',paired_with='before',method='exact')
        ref=stats.wilcoxon([1,-2,3,4,-5],method='exact')
    assert r['p']==pytest.approx(ref.pvalue)

def test_fisher_known():
    table=np.array([[1,9],[11,3]])
    rows=[(a,b) for a in range(2) for b in range(2) for _ in range(table[a,b])]
    df=pd.DataFrame(rows,columns=['a','b'])
    r=run(df,action='fisher_exact',row='a',column='b')
    assert r['p']==pytest.approx(.0027594561852200836)
    assert r['odds_ratio']==pytest.approx(1/33)

@pytest.mark.parametrize('action',['welch_anova','games_howell','kruskal_wallis','wilcoxon'])
def test_phase2_invalid_constant(action):
    df=pd.DataFrame(dict(g=['a']*3+['b']*3,y=[1]*6,x=[1]*6))
    cfg=dict(outcome='y',paired_with='x') if action=='wilcoxon' else dict(outcome='y',group='g')
    r=run(df,action=action,**cfg)
    assert r['valid'] is False

def test_fisher_not_2x2(rank_data):
    with pytest.raises(ValueError,match='2x2'):
        run(rank_data,action='fisher_exact',row='g',column='y')
