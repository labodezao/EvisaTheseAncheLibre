C     Last change:  BB    5 Apr 2016    4:46 pm
	SUBROUTINE ANCHE(OMEGA,g0,LA0,alpha,E0,V0,V1,IFLUTE,
     SRHOA,MREED,KREED,MA,KA)
C...CALCUL DES PARAMETRES D' OSCILLATEUR DE L' ANCHE AERIENNE
c...MA (masse) et KA (raideur) de l'anche sont en sortie.
C...TOUTES LES UNITES SONT MKS
	REAL LA0,MREED,KREED,MA,KA,LA
	g=g0
C...g EST LA LARGEUR DU JET OU DE L' ANCHE
	LA=LA0
C...LA EST LA DISTANCE LEVRES- BISEAU
C...OU LA LONGUEUR VIBRANTE DE L' ANCHE
	E=E0
C...E EST L' EPAISSEUR DU JET OU DE L' ANCHE
	omegac=alpha*v0/la
c...omegac est une sorte de pulsation centrale
c...qui doit tomber a peu pres au milieu de la tessiture
c...si les parametres sont bien choisis.
	V=V0+V1*(OMEGA/omegac -1.)
C...V EST LA VITESSE DU JET SI IFLUTE=0
C...V EST LE MODULE ELASTIQUE DU MATERIAU SI IFLUTE=1
C...RHOA EST LA DENSITE DE L' AIR SI IFLUTE=0

	IF(IFLUTE.EQ.1) GO TO 2
C...ON A AFFAIRE A UNE ANCHE AERIENNE
c...Pour les flutes
c...Le calcul ci-dessous utilise les parametres reels du jet
c...(vitesse, geometrie), tels qu'on peut les mesurer par 
c...des experience simples d'expiration.
c...Les experience de justesse ont montre la necessite d'un
c...couplage a l'anche, avec une frequence propre d'anche plus
c...haute que la frequence du tube pour les notes graves, et
c...plus basse pour les notes aigues.
c...c'est ce que donne la parametrisation ci dessous
c...pourvu que v1 soit suffisamment faible (si v1
c...est nul, la pulsation propre de l'anche devient meme
c...constante) 
c...
C...VALEURS pifometrees POUR LES DIFFERENTS PARAMETRES
C...POUR UNE FLUTE EN UT: g0=1.E-2 m
C...(LARGEUR DU JET=1CM POUR LA 440)
C...LA0=8.E-3 ( dist. lumiere biseau, MESURE DANS LA GLACE)
C...E0=6.E-4m  (EPAISSEUR DU JET 1MM POUR LA440,
C...0.5MM POUR LA 1760)
C...V0=20.M/S V1=0.3m/s (CONSIDERATIONS SUR LA CAPACITE DES POUMONS,
C...LA DUREE DE L' EXPIRATION ET LA SURFACE DE L' OUVERTURE DES
C...LEVRES, v = v0+ v1*(o/oc-1)  
c...oc est une pulsation
c...centrale de la tessiture, ou encore une pulsation propre
c...de l'anche, definie par oc=alpha*v/la, alpha etant
c...un parametre libre de l'ordre de 1 a 2, en principe
c..independant de l'instrument.
c...
	 ma=rhoa*e*g*la
	 ka=ma*(alpha*v/la)**2
	GO TO 3
2       CONTINUE
C...ON A AFFAIRE A UNE ANCHE SOLIDE : pas de calcul, on prend 
c...directement les paramètres M et K donnés dans le fichier d'entrée
	  MA=MREED
	  KA=KREED
C...FORMULES PRELIMINAIRES
3       OMEGAR=SQRT(KA/MA)
C...KA ET MA SONT LES PARAMETRES D' OSCILLATEUR DE L' ANCHE
C...OMEGAR EST LA PULSATION DE RESONANCE CORRESPONDANTE
c...	WRITE(6,1) MA,KA,OMEGAR
1        FORMAT(' MA=',E10.5,' KA=',E10.5,' OMEGAR=',E10.5)
	RETURN
	 END
