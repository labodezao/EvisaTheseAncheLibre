C     Last change:  BB    5 Apr 2016    3:29 pm
        SUBROUTINE PROPAG(ETA,RHOA,GAMMA,OMEGA,N,L,LP,
     s TT,TB,OFILIB,D0,D0P,DL,DLP,K,KP)
C...
C...POUR CALCULER LA CONSTANTE DE PROPAGATION K AVEC UNE FORMULE A
C...LA KIRCHHOFF.(ref mason, phys rev 31 1928 283)
C...ON FAIT LE CALCUL AU MILIEU DES DIFFERENTES SECTIONS
C...DU TUBE, CONNAISSANT TT, TB TEMPERATURES A LA TETE ET AU PIED
C...DU TUBE.(DEGRES CELSIUS).
C...........................................
C...ETA ET RHOA SONT LA VISCOSITE (1.8E-5KG.M-1.S-1) ET LA DENSITE DE
C...L' AIR (1.2KG.M-3)
C...N+1 EST LE NB DE TRONCONS DE LA LIGNE
C...L EST LE TABLEAU DES LONGUEURS DE TRONCONS DU TUBE, EN PARTANT DU BAS
C...D0, DL      ..     .. DIAMETRES ...         ..        ..
C...OFILIB.            ..RUGOSITES ...                (EN METRES)
C...........................................
C...TOUS LES ARGUMENTS SONT EN ENTREE SAUF K et KP, cstes de propagation
c...dans le tube ppal et dans les tronçons latéraux
C...
        COMPLEX K,KP,JC
        REAL L
        DIMENSION L(1),K(1),D0(1),DL(1),OFILIB(1)
	DIMENSION LP(1),KP(1),D0P(1),DLP(1)
        PI=3.14159
        JC=(0.,1.)
        DT=TT-TB
        NP1=N+1
C...........................................
C...CALCUL DE LA LONGUEUR TOTALE DU TUBE
        XTOT=0.
        DO 3 I=1,NP1
        XTOT=XTOT+L(I)
3       CONTINUE
C...BOUCLE SUR LA SECTION
        DO 1 I=1,N
C....CALCUL DE L' ABCISSE MILIEU DE SECTION PAR RAPPT AU PIED DU TUBE
        X=0.
        DO 8 J=1,I
8       X=X+L(J)
        X=X-L(I)/2.
C...CALCUL DE LA TEMPERATURE AU PT CONSIDERE, en supposant un profil 
c...de température exponentiel le long du tube, de constante 0.25 m.
C...Interpolation exponentielle ENTRE LA TEMPERATURE TETE TT ET LA TEMPERATURE
c... ambiante TB (DEG C):
	tempo = exp(-(xtot-x)/0.25)
        T=TB+DT*tempo
c...        write (6,7) T
7	FORMAT(' température tronçon = ', f10.5)
C...CALCUL DE LA VITESSE DU SON CORRESPONDANT A LADITE TEMPERATURE
C...POUR UN MILIEU SANS DISSIPATION (DEPENDANCE EN TEMPERATURE DONNEE 
C...PAR L' AIR LIQUIDE) VSON=(P0*GAMMA/RHOA))**0.5
        VSON=(329.95+0.69*T)
	ovson=omega/vson
C...L' AIR EST SUPPOSE CONTENIR 100% D' HUMIDITE ET 2.5% DE CO2
C...(REF COLTMAN, JASA 65 1979 499)
C...
C...CALCUL DE GAMMAPRIME (MASON)
        SGAMMA=SQRT(GAMMA)
        GAMMAP=SQRT(ETA)*(1.+1.581*(SGAMMA-1./SGAMMA))
C...CALCUL DU DIAMETRE MOYEN DU TUBE
        DM=(D0(I)+DL(I))/2.
	DMP=(D0P(I)+DLP(I))/2.
C...CALCUL DU PERIMETRE DU TUBE AU MILIEU DU TRONCON
        PERI=PI*OFILIB(I)*DM
        PERIP=PI*OFILIB(I)*DMP
C...CALCUL DE LA SECTION MOYENNE DU TRONCON
        SM=PI*DM**2/4.
        SMP=PI*DMP**2/4.
C...CALCUL DE LA CONSTANTE DE PROPAGATION (FORMULE DE KIRCHHOFF)
        PROVI=PERI*GAMMAP/(2.*SM*SQRT(2.*OMEGA*RHOA))
        K(I)=OVSON*((1.+PROVI)-JC*PROVI)
	if (DMP.LT.1.e-6)go to 5
        PROVIP=PERIP*GAMMAP/(2.*SMP*SQRT(2.*OMEGA*RHOA))
        KP(I)=OVSON*((1.+PROVIP)-JC*PROVIP)
	go to 6
c...pour éviter une division 0/0 dans le cas d'un trou latéral de diamètre
c...nul (correspondant en fait à un changement de perce), on met dans ce 
c...cas arbitrairement KP(I) à une valeur quelconque :
5	KP(I)= ovson
6	continue
C...DANS SON ARTICLE, MASON DONNE K=OMEGA*(PROVI+JC*(1+PROVI))/VSON
c...        WRITE(6,4) I,X,K(I),KP(I)
4       FORMAT(' N0 SECT',I6,' ABCISSE',F12.5,' K',2F12.5,' KP',2F12.5)
1       CONTINUE
c...On passe maintenant au tronçon N+1, qui est un cas particulier
c...puisqu'il n'y a pas de tronçon latéral associé.
	I=NP1
C....CALCUL DE L' ABCISSE MILIEU DE SECTION PAR RAPPT AU PIED DU TUBE
        X=0.
        DO 2 J=1,I
2       X=X+L(J)
        X=X-L(I)/2.
C...CALCUL DE LA TEMPERATURE AU PT CONSIDERE, en supposant un profil 
c...de température exponentiel le long du tube, de constante 0.25 m.
C...Interpolation exponentielle ENTRE LA TEMPERATURE TETE TT ET LA TEMPERATURE
c... ambiante TB (DEG C):
	tempo = exp(-(xtot-x)/0.25)
        T=TB+DT*tempo
c...        write (6,103) T
C...CALCUL DE LA VITESSE DU SON CORRESPONDANT A LADITE TEMPERATURE
C...POUR UN MILIEU SANS DISSIPATION (DEPENDANCE EN TEMPERATURE DONNEE 
C...PAR L' AIR LIQUIDE) VSON=(P0*GAMMA/RHOA))**0.5
        VSON=(329.95+0.69*T)
	ovson=omega/vson
C...L' AIR EST SUPPOSE CONTENIR 100% D' HUMIDITE ET 2.5% DE CO2
C...(REF COLTMAN, JASA 65 1979 499)
C...
C...CALCUL DE GAMMAPRIME (MASON)
        SGAMMA=SQRT(GAMMA)
        GAMMAP=SQRT(ETA)*(1.+1.581*(SGAMMA-1./SGAMMA))
C...CALCUL DU DIAMETRE MOYEN DU TUBE
        DM=(D0(I)+DL(I))/2.
C...CALCUL DU PERIMETRE DU TUBE AU MILIEU DU TRONCON
        PERI=PI*OFILIB(I)*DM
C...CALCUL DE LA SECTION MOYENNE DU TRONCON
        SM=PI*DM**2/4.
C...CALCUL DE LA CONSTANTE DE PROPAGATION (FORMULE DE KIRCHHOFF)
        PROVI=PERI*GAMMAP/(2.*SM*SQRT(2.*OMEGA*RHOA))
        K(I)=OVSON*((1.+PROVI)-JC*PROVI)
        RETURN
        END

