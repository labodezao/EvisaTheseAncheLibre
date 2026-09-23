C     Last change:  BB    7 Apr 2016    3:27 pm
        SUBROUTINE LCZB(LP0,CP,D0P,DLP,N,D0,DL,SP,ISTYLE,LEVEE,
     s iflute,pressn,omega,rhoa,eta,LP,zboup)
C...CALCUL DE LA LONGUEUR EFFECTIVE LP DE LT ASSOCIEE AUX TROUS
C... LATERAUX, DEBOUCHES OU NON.
c...calcul de l'impédance d'extrémité zbout associée aux trous latéraux
c...débouchés.
C...LP0=HAUTEUR DES CHEMINEES (BRUTE)
C...CP=0 OU 1 SUIVANT QUE LE TROU EST OUVERT OU FERME
C...N=NOMBRE DE TROUS, EMBOUCHURE NON COMPRISE
C...ISTYLE: 0=PAS DE CLE; 1=PLATEAU CREUX; 2=PLATEAU PLEIN
C...D=DIAMETRE DU TUBE PRINCIPAL
C...DP=DIAMETRE DES TROUS
C...LP=LONGUEUR EFFECTIVE , RESULTAT DU CALCUL
C...SI DP=0, LES CORRECTIONS DE LONGUEUR SONT NULLES.
C...POUR QUE LA BRANCHE LATERALE DU TUYAU SOIT NEGLIGEE DANS LE
C...CALCUL DE L' IMPEDANCE (ET ON VEUT QU' ELLE LE SOIT SI LE 
C...CHANGEMENT DE TRONCON CORRESPOND A UN CHANGEMENT DE PERCE ET 
C...NON A UN TROU LATERAL), IL FAUT QUE DP=0.
C...
C...CES CORRECTIONS DE LONGUEUR SONT EMPRUNTEES A NEDERVEEN
C...(ACUSTICA,28,1973, P12)
C...........................................................
C...TOUS LES ARGUMENTS SONT EN ENTREE, SAUF LP et zbou.
        INTEGER*4 ISTYLE
        REAL LP0,LP,LPC,LEVEE
        COMPLEX zboup,zboutc
        DIMENSION LP0(1),CP(1),ISTYLE(1),LEVEE(1),LP(1)
        DIMENSION D0(1),DL(1),D0P(1),DLP(1),SP(1)
        DIMENSION zboup(1),pressn(1)
        PI=3.14159
c...Calcul de flutec, qui intervient dans l'expression de la correction
c...de longueur due au jet: flutec=0.5 pour une flûte, et 1 pour un instrument
c...à anche
        IF(iflute)6,6,7
6       flutec=0.1
        GO TO 8
7       flutec=1.
8       continue
c...        PRINT*,"iflute,flutec="
c...        PRINT*,iflute,flutec
C...BOUCLE SUR LES TROUS
        DO 1 I=1,N
        R0PI=D0P(I)/2.
C...R0PI EST LE RAYON DU TROU LATERAL
        dtube=(d0(i)+dl(i+1))/2.
C...
c...Calcul de DLPI, diamètre effectif du trou latéral qui sera utilisé
c...pour le calcul de la correction de longueur intérieure.
c...Si la cheminée du trou latéral est cylindrique, on prend DLPI = le
c...diamètre du cylindre. Si le trou latéral est sous coupé, c'est plus
c...compliqué : on prend
c...pour DLPI le diamètre interne du trou latéral, si la cheminée est
c...haute devant son diamètre; On prend pour DLPI le plus petit diamètre
c...de la cheminée si la cheminée est basse devant son diamètre.
c...
        tempo1 = LP0(I)/(DLP(I)+1.e-5)
        tempo2 = EXP(-tempo1)
        dlpi1 = MIN(D0P(I), DLP(I))
        dlpi2 = DLP(I)
c....        WRITE(6,4) tempo1, tempo2, dlpi1, dlpi2
4       FORMAT(' tempo1', f10.5,' tempo2', f10.5,' dlpi1', f10.5,
     s ' dlpi2', f10.5)
        dlpi = tempo2*dlpi1 + (1.-tempo2)*dlpi2
C...CORRECTION INTERIEURE.(ON APPLIQUE CETTE CORRECTION SEULEMENT
C...SI LE TROU EST OUVERT).
        tempo3=1.-cp(i)
        CLINT=(DLPI*(1.3 - 0.9*DLPI/dtube)/2.)*tempo3
C...CORRECTION EXTERIEURE (mise à zéro depuis qu'on prend en compte
c...une impédance d'extrémité, mais avec l'expression ci-dessous pour
c...tenir compte des effets de jet).
c...Le coefficient zeta est à ajuster par fit sur l'expérience (pour négliger
c...les effets de jet, prendre zeta = 0).
c...On suppose qu'on a un faible effet de jet pour les flûtes, et un
c...fort effet pour les instruments à anche, d'où le facteur 0.1 sur flutec:
        zeta=4.
        CLOUT=zeta*pressn(i)*flutec*dlpi*tempo3
C...CORRECTIONS DE CLES
        CLEVI=0.
        CLEVO=0.
        IF(ISTYLE(I).EQ.0) GO TO 2
C...CORRECTION DE CLE EXTERIEURE (SEULEMENT SI LE TROU EST OUVERT)
C...C' EST LA CORRECTION DE CLE DONNEE PAR NEDERVEEN, DIVISEE PAR 
C...DEUX SI PLATEAUX CREUX.
        TEMPO=(R0PI/LEVEE(I))**0.39 -1.
        CLEVO=0.65*R0PI*TEMPO*(1.-CP(I))*ISTYLE(I)/2.
C...CORRECTION DE CLE INTERIEURE (SEULEMENT SI TROU FERME, ET SI
C...PLATEAU CREUX)
C...VALEUR FORFAITAIRE, INVENTEE PAR MOI, PAS ABSURDE DANS LE CAS
C...D' UNE FLUTE TRAVERSIERE A PLATEAUX CREUX.
        IF((ISTYLE(I).EQ.0).OR.(ISTYLE(I).EQ.2)) GO TO 2
        CLEVI=1.E-3*CP(I)
2       CONTINUE
        LP(I)=LP0(I)+CLOUT+CLINT+CLEVO+CLEVI
c...        WRITE(6,3) I,CP(I),LP0(I),LP(I)
3       FORMAT(' TROU N0',I6,' OUVERT?=',F10.5,' LBRUTE=',F12.5,
     S' LCORRIGE=',F12.5)
c...calcul de l'impédance d'extrémité du tronçon latéral. La subroutine zbout
c..calcule une impédance d'extrémité pour
c...tous les tronçons latéraux, même ceux
c...qui correspondent à un changement de perce et non à un vrai trou latéral.
c...Dans ce cas, l'impédance a une valeur forfaitaire grande, qui sera de
c.. toute façon inutilisée dans le calcul ltrans, à condition que lesdits "trous"
c...apparaissent comme fermés dans la table des doigtés.
        D0PC=D0P(i)
        LPC=LP0(I)
	SPC=SP(i)
        CALL zbout(omega,rhoa,ETA,D0PC,LPC,SPC,ZBOUTC)
        zboup(i)=-zboutc
c...le signe moins sur l'impédance est imposé par la convention d'orientation
c...des coordonnées au niveau des  trous latéraux.
c...	write(6,5) i,zboutc
5	format(' i=', I4,' zboup=',2F15.1)
1       CONTINUE
        RETURN
        END

