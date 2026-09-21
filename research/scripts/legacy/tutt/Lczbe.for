C     Last change:  BB    5 Apr 2016    3:27 pm
        SUBROUTINE LCZBE(NDEG,NTESSG,IFLUTE,D0N,DLN,D0NP1,DLNP1,
     SDTUBE,LCHEM,SE,LEVRES,PAREMB,omega,rhoa,eta,CLINT,CLOUT,ZBOUE)
C...calcul de CORRECTIONs DE LONGUEUR A L' EMBOUCHURE (intérieure et extérieure)
c...le programme calcule aussi une impédance d'extrémité ZBOUE.
c...Les corrections de longueur (nécessaires seulement dans le cas d'une flûte)
c...sont calculées dans cette subroutine, et effectuées dans le programme principal.

c...J'ai pu montrer que la prise en compte de l'impédance d'extrémité au niveau de
c...l'embouchure  revient à remplacer Ztube par Ztube + Zboue. Simple!
c...L'impédance d'extrémité a été prise égale à l'impédance de rayonnement pour
c...les flûtes, et a été prise nulle provisoirement pour les instruments
c...à anche, ce qui revient à négliger l'influence de la cavité buccale. Quand on
c...aura un bon modèle pour cette influence, on pourra mettre la bonne expression
c...pour l'impédance d'extrémité.
c...arguments en entrée : D0N, DLN, sont les diamètres du tronçon N
c...D0NP1, DLNP1 sont les diamètres du trou d'embouchure (éventuellement ovale).
c...SE est la surface du trou d'embouchure
C...TOUS LES ARGUMENTS SONT EN ENTREE, SAUF CLINT et CLOUT pour les
c...corrections de longueur et ZBOUE pour l'impédance.
C...
C...Le trou d'embouchure est RELIE à la fois au tube principal et à 
C...L' ESPACE EXTERIEUR PAR UNE GEOMETRIE COMPLIQUEE.
c...On le schématise ici comme un (ou deux) tronçon(s) de la ligne 
c...principale, d'une longueur corrigée pour rendre compte des détails
c...de la géométrie tridimensionnelle du système. 
c...
c...On fait 3 calculs suivant le type d'instrument, c'est à dire
c...suivant la valeur du paramètre IFLUTE : 
c...iflute = -1 : flute traversière 
c...(c'est le cas d'un trou d'embouchure allongé dans l'axe du tube);
c...iflute = 0 : flute à bec 
c...(c'est le cas d'une embouchure allongée perpendiculairement
c...à l'axe);
c...iflute = 1 : clarinette ou autre anche solide : pas de correction de longueur.
C...

        REAL LEVRES, LCHEM
        COMPLEX zboue,zboutc
        PI=3.14159
	if(iflute) 3, 4, 5
c...clarinette ou autre anche : pas de correction de longueur à l'embouchure
5	clint = 0.
	clout = 0.
        zboue=0.
	go to 6
c........................................................................
c...flûte à bec : correction de longueur pour une embouchure décrite par
c...un seul tronçon. La cheminée d'embouchure est le tronçon n° N+1,
c...corrigée à la fois des corrections de longueur intérieure et
c...extérieure, ces corrections étant données par les formules suivantes :
c...correction intérieure de type Nederveen, identique à celle utilisée
c...pour un trou latéral, avec pour diamètre de cheminée la valeur la0,
c...dimension longitudinale du trou.
c...La correction de longueur extérieure clout est une correction de bout
c... classique, calculée à partir de la dimension longitudinale du trou 
c...d'embouchure, c'est à dire la distance lumière-biseau la0. Elle est 
c...prise en compte ici via le calcul d'une impédance d'extrémité. 
c...Donc, dans la pratique, pour une flûte à bec, il faut donner dans le
c...programme principal la valeur LA0 aux deux arguments D0NP1 etDLNP1.
4	clint=DLNP1*(1.3 - 0.9*DLNP1/dtube)/2.
	clout=0.
c...        clouteq=0.35*D0NP1
        call zbout(omega,rhoa,ETA,D0NP1,LCHEM,SE,ZBOUTC)
        ZBOUE=ZBOUTC
	go to 6
c........................................................................
c...flûte traversière : correction de longueur pour une embouchure décrite
c...par deux tronçon. L'embouchure est représentée par les deux
c...tronçons n° N (pour le trou d'embouchure proprement dit) et par
c...le tronçon n° N+1 (pour l'espace situé entre le trou d'embouchure
c...et l'extérieur, et comprenant les lèvres).
c...La longueur du tronçon N est la hauteur géométrique de la cheminée,
c...corrigée pour tenir compte de la position latérale du trou, qui 
c...n'est pas dans l'axe, d'où la correction de longueur intérieure. 
c...Là encore, cette correction de longueur intérieure est du type 
c...Nederveen, calculée avec le diamètre effectif du trou d'embouchure, 
c...comme pour un trou latéral sous coupé.
c...La correction de longueur intérieure s'applique au tronçon n° N; 
c...La correction de longueur extérieure s'applique au tronçon n° N+1, 
c...et est purement calée sur l'expérience.Elle est 
c...prise en compte ici via le calcul d'une impédance d'extrémité.
c...Dans la pratique, pour une flûte traversière, il faut donner dans le
c...programme principal la valeur géométrique de la cheminée d'embouchure
c...aux paramètres D0N, DLN et LCHEM. Quant à D0NP1 et DLNP1, il faut leur
c...donner une valeur correspondant à la surface du trou d'embouchure
c...laissée libre par le recouvrement des lèvres.
3       tempo1= LCHEM/DLN
        tempo2= EXP(-tempo1)
        dln1=MIN(D0N, DLN)
        dln2=DLN
        dlneff=tempo2*dln1+(1.-tempo2)*dln2
	clint=dlneff*(1.3 - 0.9*dlneff/dtube)/2.
        X=FLOAT(NDEG)-FLOAT(NTESSG)/2.
	clout=0.
	D0PC=(levres*x+paremb)*d0np1/(2.*0.35)
c...        clouteq=0.35*D0PC
        call zbout(omega,rhoa,ETA,D0PC,LCHEM,SE,ZBOUTC)
        zboue=zboutc
C...La géométrie du tronçon n° N+1 EST MODELISEE ICI PAR 2 PARAMETRES: 
c...PAREMB ET LEVRES, POUR DECRIRE RESPECTIVEMENT LA PARTIE CONSTANTE ET
C...VARIABLE EN FONCTION DU DEGRE DE LA GAMME D' UNE CORRECTION
C...DE LONGUEUR LIEE A LA COUVERTURE DES LEVRES A L' EMBOUCHURE.
C...
C...PAREMB EST UN FACTEUR DE CORRECTION DE LONGUEUR POUR UNE
C...COUVERTURE MOYENNE DE L' EMBOUCHURE.
C...LEVRES EST POUR TENIR COMPTE DE LA partie de la COUVERTURE 
c...A L' EMBOUCHURE QUI EST VARIABLE SUIVANT LA FREQUENCE.
c......................................................................
6	continue
c...        WRITE(6,2) LEVRES,PAREMB
2       FORMAT(' LEVRES=',F10.5,' PAREMB=',F10.5)
c...    	write(6,1) clint, clouteq
1	format(' clint=', F10.5,'  clouteq =',F10.5)
c...	write(6,7) zboue
7	format(' zboue=',2F15.1)
        RETURN
        END

