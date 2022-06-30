;;; Directory Local Variables
;;; For more information see (info "(emacs) Directory Variables")

((python-mode . ((eval . (let ((path (concat (locate-dominating-file buffer-file-name ".dir-locals.el") "bkmkorg")))
                           ;; add to Anaconda path
                           (pushnew path python-shell-extra-pythonpaths :test 'equal )
                           ;; add to pyright path
                           (setq-default lsp-pyright-extra-paths (vector path))))
                 ;; set the conda env name
                 (conda-project-env-path . "bookmark")
                 ;; activate the conda env
                 (eval . (+jg-conda-env-activate))
                 )
              )
 )
