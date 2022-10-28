from email.policy import default
from flask import Flask, session, redirect, url_for, escape, request, Response, render_template, Markup, make_response
import hashlib
import sys
from functools import wraps
import sqlite3
import os
import werkzeug.exceptions
import wtforms
from wtforms import Form, BooleanField, StringField, validators, IntegerField, SelectField, widgets, SelectMultipleField, ValidationError, RadioField, DecimalField
from wtforms.validators import NumberRange
from polyglot import PolyglotForm
import mimetypes

from jinja2 import Template, Environment, FileSystemLoader
import json
import urllib
from urllib.parse import urlencode, quote_plus

app = Flask(__name__)
# set the secret key.  keep this really secret:
app.secret_key = '"\xf9$T\x88\xefT8[\xf1\xc4Y-r@\t\xec!5d\xf9\xcc\xa2\xaa'

@app.route('/', methods=['GET', 'POST'])
def linkki():

    # Asetustiedosto
    with urllib.request.urlopen('https://europe-west1-ties4080.cloudfunctions.net/vt2_taso1') as response:
        data = json.load(response)

    # Palauttaa arvon 1 "Peru edellinen" -nappia painettaessa.
    try:
        peruEdellinenSiirto = int((request.values.get("peruEdellinenSiirto")))
    except:
        peruEdellinenSiirto = 0

    # Palauttaa edellisen siirtoparin mahdollista poistoa varten.
    try:
        siirtopari = [int(json.loads( request.values.get("poistetut"))[0]), int((request.values.get("siirtokohde")))]
    except:
        siirtopari = [-1,-1]

    # Siirtohistoria
    try:
        siirtoparit = json.loads( request.values.get("siirtoparit") )
    except:
        siirtoparit = []

    # Lisätään viimeinen siirtopari siirtohistoriaan.
    try:
        if siirtopari != [-1, -1]:
            siirtoparit.append(siirtopari)
    except:
        pass

    # Siirrettävän nappulan uusi ruutu.
    try:
        siirtokohde = int((request.values.get("siirtokohde")))
    except:
        siirtokohde = -1

    # 0 = poistotila, 1 = siirtotila
    try:
        tila = int((request.values.get("tila")))
    except:
        tila = 0

    # Laudan minimikoko
    try:
        minimikoko = data["min"]
    except:
        minimikoko = 8

    # Laudan maksimikoko
    try:
        maksimikoko = data["max"]
    except:
        maksimikoko = 16

    # Palauttaa true myöhemmin, jos lomakkeessa puutteita eikä alusteta pelaajien nimikenttiä.
    tayttamaton = False

    # Laudan koko
    try:
        koko = int(request.values.get("x"))
    except:
        try:
            koko = int(request.form.get("laudanKoko"))
        except:
            koko = minimikoko

    # Alustetaan lauta minimikokoiseksi, jos annetaan liian pieni tai suuri koko
    if koko < minimikoko or koko > maksimikoko:
        koko = minimikoko
        tayttamaton = True
        
    p1 = ""
    p2 = ""
    
    # Alustetaan pelaajanimet
    if tayttamaton == False:
        if request.args.get("pelaaja1") is None:  # and len(request.form.get("pelaaja1", "Pelaaja1")) > 0
            if len(request.form.get("pelaaja1", "Pelaaja 1")) > 0:
                p1 = request.form.get("pelaaja1", "")
            else:
                p1 = ""
                tayttamaton = True
        else:
            p1 = request.args.get("pelaaja1")

        if tayttamaton == False:
            if request.args.get("pelaaja2") is None:  # and len(request.form.get("pelaaja1", "Pelaaja1")) > 0
                if request.form.get("pelaaja2") is not None and len(request.form.get("pelaaja2")) > 0:
                    p2 = request.form.get("pelaaja2", "")
                else:
                    p1 = ""
                    p2 = ""
                    tayttamaton = True
            else:
                p2 = request.args.get("pelaaja2")

    if tayttamaton == True:
        koko = minimikoko

    # Palauttaa 1, jos punainen, eli aiemmin palautettu.
    try:
        siirrettavanVari = int( request.args.get("siirrettavanVari") )
    except:
        siirrettavanVari = -1

    # Viimeksi poistettu nappula.
    try:
        viimeksiPoistettu = int( request.args.get("viimeksiPoistettu") )
    except:
        viimeksiPoistettu = None

    # Valittu nappula
    try:
        if tila == 1:
            valittu = viimeksiPoistettu
        else:
            valittu == -1
    except:
        valittu = -1

    # Historia poistetuista napeista mahdollista palautusta varten.
    try:
        poistetut = json.loads( request.values.get("poistetut") )
    except:
        poistetut = []

    # Lisätään viimeksi poistettu historiaan.
    try:
        if int(viimeksiPoistettu) > -1:
            poistetut.append(int(viimeksiPoistettu))
    except:
        pass

    # Siirrettävä nappula.
    try:
        siirrettava = poistetut[len(poistetut)-1]
    except:
        siirrettava = -1

    # Palauttaa 1, jos tarvitsee poistaa edellinen poisto.
    try:
        peruEdellinen = int(request.args.get("peruEdellinen"))
    except:
        peruEdellinen = 0

    # Palautettujen nappuloiden sijainti
    try:
        palautetut = json.loads( request.values.get("palautetut") )
    except:
        palautetut = []

    try:
        pelilauta = json.loads( request.values.get("lauta") )
    except:
        pelilauta = []

    # Tyhjentää laudan muokkaushistorian tilaa vaihdettaessa
    try:
        tyhjaaHistoria = int((request.values.get("tyhjaaHistoria")))
    except:
        tyhjaaHistoria = 0

    if tyhjaaHistoria == 1:
        poistetut= []
        siirtoparit = []

    # Muokataan olemassa olevaa pelilautaa.
    if pelilauta != []:

        for u in range(len(pelilauta)):
            pelilauta[str(u)]["valittu"] = 0

        try:
            if tila == 0:
                pelilauta[str(viimeksiPoistettu)]['a'] = 0
            if tila == 1:
                pelilauta[str(viimeksiPoistettu)]["valittu"] = 1
        except:
            pass

        # Suoritetaan siirto, jos ollaan siirtotilassa
        try:
            if tila == 1 and viimeksiPoistettu == -1:
                pelilauta[str(siirrettava)]['a'] = 0
                pelilauta[str(siirtokohde)]['a'] = 1
                pelilauta[str(siirtokohde)]['p'] = siirrettavanVari
                poistetut.pop()
        except:
            pass

        # Perutaan edellinen poisto
        if peruEdellinen == 1:
            if poistetut[len(poistetut)-1] not in palautetut:
                palautetut.append(poistetut[len(poistetut)-1])
            pelilauta[str(poistetut[len(poistetut)-1])]['a'] = 1
            pelilauta[str(poistetut[len(poistetut)-1])]['p'] = 1
            poistetut.pop()

        # Perutaan edellinen siirto
        if peruEdellinenSiirto == 1:
            pelilauta[str(siirtoparit[len(siirtoparit)-1][0])]['a'] = 1
            pelilauta[str(siirtoparit[len(siirtoparit)-1][1])]['a'] = 0
            siirtoparit.pop()

    # Alustetaan pelilauta.
    else:
        pelilauta = {}
        ruutu = {}
        vari = 1
        palautettu = 0
        arvo = 0
        rivinumero = 1
        testailu = []

        try:
            if data["first"] == "white":
                vari = 0
        except:
            vari = 1

        if koko%2 == 0:
            if vari == 1:
                vari = 0
            else:
                vari = 1

        for j in range(koko*koko):

            if koko%2 == 0:
                if vari == 1:
                    if (j)%koko != 0:
                        vari = 0
                else:
                    if j%koko != 0:
                        vari = 1
            else:
                if vari == 1:
                    vari = 0
                else:
                    vari = 1

            if (data["balls"] == "top-to-bottom"):
                if j == (koko*(rivinumero-1))+rivinumero-1:
                    arvo = 1
            else:
                if (j+rivinumero)%koko == 0 and j != 0:
                        arvo = 1

                if j == koko*koko-koko and j != 0:
                    arvo = 1

                testailu.append(rivinumero)

            ruutu = {

            # a = arvo = onko ruudussa nappula, p = palautettu = onko ruutuun palautettu nappula
            str(j): {
            	"v": vari,
            	"a": arvo,
                "p": 0,
                "valittu": 0
                 },
            }

            pelilauta.update(ruutu)
            ruutu = {}
            arvo = 0

            if j%koko == 0 and j != 0:
                rivinumero = rivinumero+1

    try:
        pelaajakentta1 = (request.args.get("pelaaja1"))
    except:
        pelaajakentta1 = ""
    try:
        pelaajakentta2 = (request.args.get("pelaaja2"))
    except:
        pelaajakentta2 = ""
    try:
        laudanKokoKentta = int((request.args.get("x")))
    except:
        laudanKokoKentta = minimikoko

    class Arvosanalaskuri(PolyglotForm):
    

        laudanKoko = IntegerField('Laudan koko', default=laudanKokoKentta, validators=[NumberRange(min=minimikoko, max=maksimikoko)])

        def validate_laudanKoko(form, field):
            try:
                if request.args.get("x") is not None:
                    if int(request.args.get("x")) < minimikoko or int(request.args.get("x")) > maksimikoko:
                        raise ValidationError("Syöttämäsi arvo ei kelpaa")
            except:
                raise ValidationError("Syöttämäsi arvo ei kelpaa")

            try:
                if int( request.form.get("laudanKoko", minimikoko)) < minimikoko or int( request.form.get("laudanKoko", minimikoko)) > maksimikoko:
                    raise ValidationError("Syöttämäsi arvo ei kelpaa")
            except:
                raise ValidationError("Syöttämäsi arvo ei kelpaa")

        pelaaja1 = StringField('Pelaaja 1', default=pelaajakentta1)
        def validate_pelaaja1(form, field):
            if len(request.form.get("pelaaja1", "Pelaaja 1")) < 1:
                raise ValidationError("Täytä kenttä")

        pelaaja2 = StringField('Pelaaja 2', default=pelaajakentta2)
        def validate_pelaaja2(form, field):
            if len(request.form.get("pelaaja2", "Pelaaja 2")) < 1:
                raise ValidationError("Täytä kenttä")

    form = Arvosanalaskuri()

    if request.method == 'POST':
        form.validate()

    if request.method == "POST":
       form.validate()
    elif request.method == "GET" and request.args:
       form = Arvosanalaskuri(request.args)
       form.validate()
    else:
       form = Arvosanalaskuri()

    parametrit = urllib.parse.urlencode({
        "x": koko,
	    "pelaaja1": p1,
        "pelaaja2": p2,
        "poistetut": json.dumps(poistetut),
        "palautetut": json.dumps(palautetut),
        "siirtoparit": json.dumps(siirtoparit),
	})

    

    return Response(render_template("jinja.html", siirrettavanVari=siirrettavanVari, peruEdellinenSiirto=peruEdellinenSiirto, siirtopari=siirtopari, siirtokohde=siirtokohde, valittu=valittu, tila=tila, siirtoparit=siirtoparit, palautetut=palautetut, poistetut=poistetut, viimeksiPoistettu=viimeksiPoistettu,koko=koko,pelilauta=pelilauta, lauta_json=json.dumps(pelilauta), parametrit=parametrit, form=form, p1=p1, p2=p2), mimetype='application/xhtml+xml; charset=utf-8')