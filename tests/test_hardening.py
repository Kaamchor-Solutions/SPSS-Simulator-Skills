import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from test_analyze import run_cli_on_files, run_cli

class SecondAuditRegressionTests(unittest.TestCase):
    def run_data(self,text,cfg):
        return run_cli_on_files({'data.csv':text},{'file':'data.csv',**cfg})
    def test_duplicate_selections_rejected(self):
        for action,fields in [('alpha',{'variables':['x','x']}),('correlation',{'variables':['x','x']}),('regression',{'outcome':'y','predictors':['x','x']}),('crosstab',{'row':'x','column':'x'})]:
            with self.subTest(action=action):
                code,_,err=self.run_data('x,y\n1,3\n2,5\n3,7\n4,9\n',{'action':action,**fields})
                self.assertEqual(code,2);self.assertIn('distinct',err)
    def test_empty_selections_rejected(self):
        for action in ['frequencies','describe','alpha','correlation']:
            with self.subTest(action=action):
                code,_,_=self.run_data('x\n1\n2\n',{'action':action,'variables':[]});self.assertEqual(code,2)
    def test_anova_group_name_collision(self):
        code,out,err=self.run_data('__y,y\na,1\na,1\na,2\nb,1\nb,2\nb,2\n',{'action':'anova','group':'__y','outcome':'y'})
        self.assertEqual(code,0,err);self.assertAlmostEqual(out['F'],.5);self.assertAlmostEqual(out['p'],.5185185185)
        self.assertEqual([g['group'] for g in out['groups']],['a','b'])
    def test_const_predictor_name(self):
        code,out,err=self.run_data('const,y\n1,3\n2,5\n3,7\n4,9\n5,11\n',{'action':'regression','outcome':'y','predictors':['const']})
        self.assertEqual(code,0,err);self.assertAlmostEqual(out['terms']['const']['B'],2);self.assertAlmostEqual(out['terms']['_const']['B'],1)
    def test_nonfinite_values_rejected_all_procedures(self):
        cases=[{'action':'inventory'},{'action':'describe','variables':['x']},{'action':'frequencies','variables':['x']},{'action':'crosstab','row':'g','column':'x'},{'action':'ttest','group':'g','outcome':'x'},{'action':'ttest','paired_with':'y','outcome':'x'},{'action':'anova','group':'g','outcome':'x'},{'action':'correlation','variables':['x','y']},{'action':'regression','outcome':'x','predictors':['y']},{'action':'regression','outcome':'b','predictors':['x'],'model':'logistic'},{'action':'alpha','variables':['x','y']}]
        for value in ['inf','-inf']:
            for cfg in cases:
                with self.subTest(value=value,cfg=cfg):
                    code,_,err=self.run_data(f'g,x,y,b\na,1,2,0\na,2,3,1\na,{value},4,0\nb,4,5,1\nb,5,6,0\nb,6,7,1\n',cfg)
                    self.assertEqual(code,2);self.assertIn('Nonfinite',err)
    def test_constant_correlation_invalid(self):
        code,out,_=self.run_data('x,y\n1,1\n1,2\n1,3\n1,4\n',{'action':'correlation','variables':['x','y']})
        self.assertEqual(code,0);self.assertFalse(out['valid']);self.assertFalse(out['pairs'][0]['valid']);self.assertIn('Constant',out['pairs'][0]['reason'])
    def test_zero_variance_paired_invalid(self):
        code,out,_=self.run_data('x,y\n1,1\n2,2\n3,3\n',{'action':'ttest','outcome':'y','paired_with':'x'})
        self.assertEqual(code,0);self.assertFalse(out['valid']);self.assertEqual(out['status'],'invalid')
    def test_zero_variance_independent_invalid(self):
        code,out,_=self.run_data('g,y\na,1\na,1\nb,2\nb,2\n',{'action':'ttest','outcome':'y','group':'g'})
        self.assertEqual(code,0);self.assertFalse(out['valid'])
    def test_zero_variance_anova_invalid(self):
        code,out,_=self.run_data('g,y\na,1\na,1\nb,2\nb,2\n',{'action':'anova','outcome':'y','group':'g'})
        self.assertEqual(code,0);self.assertFalse(out['valid'])
    def test_zero_variance_alpha_invalid(self):
        code,out,_=self.run_data('x,y\n1,2\n1,2\n1,2\n',{'action':'alpha','variables':['x','y']})
        self.assertEqual(code,0);self.assertFalse(out['valid'])
    def test_one_category_crosstab_invalid(self):
        code,out,_=self.run_data('g,y\na,0\na,1\na,0\n',{'action':'crosstab','row':'g','column':'y'})
        self.assertEqual(code,0);self.assertFalse(out['valid']);self.assertNotIn('p_two_sided',out)
    def test_separated_logit_not_usable(self):
        code,out,err=self.run_data('x,y\n1,0\n2,0\n3,0\n4,1\n5,1\n6,1\n',{'action':'regression','outcome':'y','predictors':['x'],'model':'logistic'})
        # Some statsmodels versions stop with a singularity/separation exception.
        if code==0:
            self.assertFalse(out['valid']);self.assertIn('converged',out);self.assertNotIn('terms',out)
        else:
            self.assertEqual(code,2);self.assertTrue('Singular' in err or 'separation' in err.lower(),err)
    def test_dropped_anova_group_counts(self):
        code,out,_=self.run_data('g,y\na,1\na,2\nb,4\nb,5\nc,9\nc,oops\n',{'action':'anova','group':'g','outcome':'y'})
        self.assertEqual(code,0);g=next(e for e in out['data_audit']['exclusions'] if e.get('group')=='c');self.assertEqual(g['count'],2);self.assertEqual(g['usable_n'],1)
    def test_sav_label_override_rejected(self):
        import tempfile
        import pandas as pd
        import pyreadstat
        with tempfile.TemporaryDirectory() as tmp:
            sav=Path(tmp)/"labelled.sav"
            pyreadstat.write_sav(pd.DataFrame({"event":[0,1,0,1]}),sav,variable_value_labels={"event":{0:"No",1:"Yes"}})
            code,_,err=run_cli({"file":str(sav),"action":"inventory","read_spss":{"convert_categoricals":True}})
            self.assertEqual(code,2);self.assertIn("underlying codes",err)
    def test_invalid_config_schema(self):
        for cfg in [[],{'action':None}]:
            code,_,err=run_cli(cfg);self.assertEqual(code,2);self.assertIn('ValueError',err)
