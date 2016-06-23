import unittest
from context import bkmkorg
# from myprog import myprog as prog
# from myprog import secondprog


class TestStringMethods(unittest.TestCase):

    def test_upper(self):
        self.assertEqual('foo'.upper(),'FOO')

    # def test_testFunc(self):
    #     self.assertEqual(prog.testFunc(2),4)
        
    # def test_secondFunc(self):
    #     self.assertEqual(myprog.secondprog.secondFunc(2),5)

    # def test_scope(self):
    #     print('testing scope')
    #     prog.scopeTest()
        
        
if __name__ == '__main__':
    unittest.main()
