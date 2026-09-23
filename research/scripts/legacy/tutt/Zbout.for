C     Last change:  BB    7 Apr 2016    4:37 pm
        SUBROUTINE ZBOUT(omega,rhoa,ETA,D0C,LC,S,ZBOUTC)
C...POUR CALCULER l'impédance d'extrémité d'un tuyau de diamètre
c...d'extrémité D0C et de longueur LC, de surface S, en tenant compte
c...du rayonnement et des pertes de charge localisées au bout.
c...On donne indépendamment le diamètre et la surface pour pouvoir 
c...traiter le cas de trous ovales. Dans ce cas, D0C est le diamètre
c...du trou dans la direction longitudinale.
c...Pour évaluer la perte de charge dans le trou ouvert, on utilise 
c...la formule de stokes, qui suppose un écoulement laminaire. 
c...C'est uniquement sous ces conditions qu'il y a proportionnalité entre 
c...pression et débit. Tutt reste dans l'hypothèse de l'acoustique
c...linéaire des petites oscillations.
C... On suppose le trou ouvert, son état réel ouvert ou fermé sera pris
c...en compte dans LTRANS.
C...........................................
C...ETA ET RHOA SONT LA VISCOSITE (1.8E-5KG.M-1.S-1) ET LA DENSITE DE
C...L' AIR (1.2KG.M-3)
C...
C...TOUS LES ARGUMENTS SONT EN ENTREE SAUF ZBOUTC, impédance d'extrémité.
C...
        COMPLEX zboutc,zboutr,zboutv,tempo1,tempo2,jc
        REAL LC
        PI=3.14159
        JC=(0.,1.)
        VSON=343.75
C...L' AIR EST SUPPOSE CONTENIR 100% D' HUMIDITE, 2.5% DE CO2 et être à 20°C
C...(REF COLTMAN, JASA 65 1979 499)
c...attention : ce CLOUT n'est pas traité ici comme une correction de 
c...longueur, mais comme un ingrédient dans l'expression de l'impédance
c...de rayonnement:
        clout = 0.35*D0C
c...warning si on a affaire à un trou latéral trop petit pour que le calcul
c...de son impédance ait un sens
        IF(D0C.LT.1.e-6) GO TO 1
c...Impédance de rayonnement
        tempo1=JC*rhoa*omega*clout
	tempo2=1.-JC*OMEGA*CLOUT/VSON
c...	tempo2=1.
	zboutr=tempo1*tempo2/S
c...impédance liée à la perte de charge dans la cheminée
	zboutv=7.5*pi*LC*eta*rhoa/S**2
c...        zboutv=0.
c...impédance d'extrémité totale
	zboutc=zboutr+zboutv
        GO TO 2
1	zboutc=1.e10*JC
c...normalement, cette valeur de l'impédance ne sera pas utilisée dans ltrans
c...car un trou de très petit diamètre doit correspondre en fait à un
c...changement de perce et non à un trou  latéral véritable. A ce titre, il
c...doit correspondre à CP(i) = 1 dans la table des doigtés (trou fermé).
c..	write(6,3) zboutc,zboutr,zboutv
3	format(' zc',2F15.1,' zr',2F15.1,' zv',2F15.1)
2       continue
        RETURN
        END

