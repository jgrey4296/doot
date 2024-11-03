.. ..  rst_tests.rst -*- mode: ReST -*-

=========
RST Tests
=========

.. contents:: Contents
   :local:


Math Test
#########

.. math::
   :name: Fourier transform

   (\mathcal{F}f)(y)
    = \frac{1}{\sqrt{2\pi}^{\ n}}
      \int_{\mathbb{R}^n} f(x)\,
      e^{-\mathrm{i} y \cdot x} \,\mathrm{d} x.



Container Test
##############

.. container:: jgcontainer

    .. productionlist:: prodlist
        action  : "{" "do" "=" `str` ["," arglist] ["," kwarg]+ "}"
        arglist : "args"   "=" "[" `arg` ["," `arg`]+ "]"
        kwarg   : `var`    "=" `val`


-------------

.. container:: jgcontainer

   .. code-block:: python
      :name: this.py
      :linenos:

      print('This is inside a container blah')

-------------

Custom Directive Test
#####################

before the directive

.. jgdir::

   blah

after the directive


Custom Transform Test
#####################

blah blah blah
