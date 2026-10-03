function [tree] = sci_matkm(tree)
// Copyright INRIA (Généré par M2SCI)
// Fonction de conversion pour Matlab matkm()
// Entrée : tree = Matlab funcall tree
// Sortie : tree = équivalent Scilab pour tree
// dims(i,:) est le vecteur dimensions du ième argument de sortie
dims=list(list(0,0),list(0,0))
// dims(i,:) est le vecteur dimensions du ième argument de sortie
vtype=[1;1]
// prop(i) est la propriété du ième argument de sortie
prop=[0;0]
for k=1:lhs
  tree.lhs(k).dims=dims(k)
  tree.lhs(k).vtype=vtype(k)
  tree.lhs(k).property=prop(k)
end
endfunction
