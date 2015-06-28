#!/bin/sh

alias ghc="ghc -O3 -ferror-spans -W -fspec-constr -threaded -rtsopts -XOverloadedStrings -XTemplateHaskell -XNoMonomorphismRestriction -XFlexibleContexts -XArrows"

ghc Main.hs -o main
rm *.hi *.o *.dyn_hi *.dyn_o
