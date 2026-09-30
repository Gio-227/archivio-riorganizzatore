# Semantica — dominio FINANZIARIO (doppio asse + firmati)

Doppia classificazione: asse **fiscale** (come lo vede il commercialista) e asse **gestionale**
(come lo usa l'imprenditore per capire il business).

## 1. Estrazione dati strutturati

Per documento: tipo (fattura attiva/passiva, nota credito, ricevuta…) · fornitore/cliente · data
emissione · scadenza · importo lordo · IVA (aliquota + importo) · netto · descrizione · numero.

## 2. Doppia categorizzazione

- **Fiscale standard:** fatture attive · passive · note credito · estratti conto · ricevute · F24 · dichiarazioni.
- **Gestionale personalizzato:** esattamente le categorie indicate dall'utente nel briefing. Non aggiungerne senza chiedere.

## 3. File firmati come gruppo solidale

`.pdf` + `-signed.pdf` + `.pdf.p7m` dello stesso atto: trattali come **un solo gruppo**, mai
separati. Il `.p7m` è il contenitore firmato (CAdES) dello stesso documento.

## 4. Anomalie → badge VERIFICA

IVA incoerente con la descrizione · importi fuori media fornitore · date fuori sequenza (fattura
con data successiva alla nota credito correlata) · duplicati (stesso numero + fornitore + data) ·
nome "fattura" ma contenuto non finanziario.

## 5. Output — Riepilogo con totali

ASSE FISCALE e ASSE GESTIONALE, per categoria: N documenti + totale €. ANOMALIE RILEVATE: N, con
file e badge VERIFICA.
