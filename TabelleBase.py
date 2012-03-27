# -*- encoding: utf-8 -*-

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from operator import itemgetter

import netsvc
import pooler
from osv import fields, osv
import decimal_precision as dp
from tools.translate import _


class account_account(osv.osv):
    
    _inherit = 'account.account'
    _columns = {
                'righe_saldi': fields.one2many('account.account_progr', 'conto', 'Saldi annui', required=False),
                'sez_bilancio':fields.selection([("AT", "Attività"),
                                                ('PA', 'Passività'),
                                                ('CO', 'Costi'),
                                                ('RI', 'Ricavi'),
                                                ('OR', 'Conti Dordine '),
                                                ],"Sez.Bilancio"),       
                'tipo_sottoconto':fields.selection([("CA", "Cassa"),
                                                    ('CL', 'Clienti'),
                                                    ('FO', 'Fornitori'),
                                                ('BA', 'Banche'),
                                                ('MC', 'Costi Magazzino'),
                                                ('MR', 'Ricavi Magazzino'),
                                                ('AM', 'Ammortamenti '),
                                                ('IV', 'Iva '),
                                                ('RI', 'Riepilogo '),
                                                ('GE', 'Generico '),
                                                ],"Tipo.Sottoconto"),                 
        
    }

account_account()


class account_account_progr(osv.osv):
    _name = 'account.account_progr'
    _description = ' Progressivi per Anno fiscale dei conti'
    
    def _calcolo_saldo(self, cr, uid, ids, field_name, arg, context=None):
     res = {}
     #
     for progre in self.browse(cr, uid, ids, context=context):
         res[progre.id] = { 'saldo_attuale': 0}
         val = progre.dare_periodo-progre.avere_periodo
         res[progre.id]['saldo_attuale'] = val
     return res

    _columns = {
                'fiscalyear_id': fields.many2one('account.fiscalyear', 'Fiscal Year', required=True, select=True),
                'conto':fields.many2one('account.account', "Conto",  required=True, select=True),
                'dare_iniziale': fields.float('Saldo Dare Iniziale', digits_compute=dp.get_precision('Account')),
                'avere_iniziale': fields.float('Saldo Avere Iniziale', digits_compute=dp.get_precision('Account')),
                'dare_periodo': fields.float('Saldo Dare Periodo', digits_compute=dp.get_precision('Account')),
                'avere_periodo': fields.float('Saldo Avere Periodo', digits_compute=dp.get_precision('Account')),
                'dare_finale': fields.float('Saldo Dare Finale', digits_compute=dp.get_precision('Account')),
                'avere_finale': fields.float('Saldo Avere Finale', digits_compute=dp.get_precision('Account')),
                'saldo_attuale':fields.function(_calcolo_saldo, method=True, digits_compute=dp.get_precision('Account'), string='Saldo Attuale', store=True, multi='sums'),

    }

account_account_progr()


class account_fiscalyear_protocolli(osv.osv):
    _name = 'account.fiscalyear.protocolli'
    _description = ' Utilizzi del credito iva di inizio anno'
    
    _columns = {
                'fiscalyear_id': fields.many2one('account.fiscalyear', 'Fiscal Year', required=True, select=True),
                'tipo_registro':fields.selection([("VE", "Vendite"),
                                                ('AC', 'Acquisti'),
                                                ('CS', 'Corrispettivi Scorporo'),
                                                ('CV', 'Corrispettivi Ventilazione'),
                                                ('SO', 'Sospensione'),
                                               ],"Tipo Registro"),
                'num_registro_iva':fields.integer('Numero Registro ', required=True,select=True),                
                'protocollo':fields.integer('Numero Protocollo ', required=False),
                'data_registrazione': fields.date('Data Registrazione', required=False,),
               }
    
account_fiscalyear_protocolli()

class account_fiscalyear_iva_crediti(osv.osv):
    _name = 'account.fiscalyear.iva.crediti'
    _description = ' Utilizzi del credito iva di inizio anno'
    _columns = {
                'fiscalyear_id': fields.many2one('account.fiscalyear', 'Fiscal Year', required=True, select=True),
                'data_utilizzo':fields.date('Data Utilizzo', required=True),
                'tipo_utilizzo':fields.selection([
                                                  ('F24', 'Utilizzo in F24'),
                                                  ('IVA', 'Utilizzo in Liquidazione Iva')
                                                  ], "Tipo Utilizzo Iva", size=15, required=True),
                'importo_utilizzato': fields.float('Importo Utilizzato', digits_compute=dp.get_precision('Account')),
                }
    

account_fiscalyear_iva_crediti()

class account_fiscalyear(osv.osv):
    _inherit = "account.fiscalyear"
    _columns = {


                'tipo_liquidazione': fields.selection([('M', 'Mensile'),
                                                    ('T', 'Trimestrale'),
                                                 ], 'Tipo Liquidazione Iva', size=15, required=True,),
                'plafond_iniziale': fields.float('Plafond Iva Inizio Anno', digits_compute=dp.get_precision('Account')),
                'plafond_residuo': fields.float('Plafond Iva Residuo', digits_compute=dp.get_precision('Account')),
                'credito_iva_iniziale': fields.float('Credito Iva Inizio Anno', digits_compute=dp.get_precision('Account')),
                'debito_iva_27': fields.float('Debito Iva Art.27-33', digits_compute=dp.get_precision('Account')),
                'percentuale_prorata': fields.float('Percentuale prorata', digits=(7, 3)),
                'maggiorazione_trimestrale': fields.float('% Maggiorrazione iva Trimestrale', digits=(7, 3)),
                'perc_acconto_iva': fields.float('% Acconto Iva', digits=(7, 3)),
                'acconto_iva': fields.float('Acconto iva di Dicembre', digits_compute=dp.get_precision('Account')),
                'versamento_minimo': fields.float('Versamento Minimo', digits_compute=dp.get_precision('Account')),
                'righe_utilizzi_crediti': fields.one2many('account.fiscalyear.iva.crediti', 'fiscalyear_id', 'Righe Utlizzi Crediti', required=False),
                'righe_protocolli': fields.one2many('account.fiscalyear.protocolli', 'fiscalyear_id', 'Ultimi Protocolli Registri', required=False),
                }

account_fiscalyear()            


class account_tax(osv.osv):
      _inherit = 'account.tax'
      _columns = {
                  'indetraibile':fields.boolean('flag iva indetraibile'),
                  }
      
    
account_tax()  


class account_registri_period(osv.osv):
    _name = 'account.registri_period'
    ''' Tabella con i progressivi di periodo generale
     
     '''
    _columns = {
                'period_id': fields.many2one('account.period', 'Period', required=True, ondelete="cascade"),
                'fiscalyear_id': fields.related('period_id', 'fiscalyear_id', string='Fiscal Year', type='many2one', relation='account.fiscalyear'),
                'tipo_registro':fields.selection([("VE", "Vendite"),
                                                ('AC', 'Acquisti'),
                                                ('CS', 'Corrispettivi Scorporo'),
                                                ('CV', 'Corrispettivi Ventilazione'),
                                                ('SO', 'Sospensione'),
                                                ('LG','Libro Giornale')
                                               ],"Tipo Registro"),
                
               'num_registro_iva':fields.integer('Numero Registro ', required=True,select=True),                                                
               'ultima_pagina': fields.float('ultima pagina stampata', digits=(7, 0)),
               'ultima_riga_tipog':fields.float('ultima riga stampata', digits=(7, 0), help='Ultima riga Stampata sul libro Giornale'),
               'totale_dare': fields.float('Toatle Dare', help='Totale del Periodo Libro Giornale', digits_compute=dp.get_precision('Account')),
               'totale_avere': fields.float('Totale Avere', help='Totale del Periodo Libro Giornale', digits_compute=dp.get_precision('Account')),
               'data_ultima_riga': fields.date('Data ultima Riga', help='Data dell ultima riga stampata del periodo', required=False),
               'data_ultima_stampa': fields.date('Data ultima Riga', help='Data dell ultima stampa e quindi del calcolo dei progressivi del periodo', required=False),
               'data_versamento': fields.date('Data Versamento', help='Data dell eventuale versamento, solo sul registro di liquidazione', required=False),
               'banca_versamento':fields.many2one('res.partner.bank', 'Banca di Versamento', required=False, help="Banca del Azienda "),
               'importo_iva_credito': fields.float('Iva a Credito', help='Importo iva a Credito Calcolata nel periodo', digits_compute=dp.get_precision('Account')),
               'importo_iva_dovuta': fields.float('Iva a dovuta', help='Importo iva a Dovuta Calcolata nel periodo', digits_compute=dp.get_precision('Account')),
               'righe_progressivi_iva': fields.one2many('progressivi.iva.period', 'period_registro_id', 'Righe Progressivi Iva', required=True),
                }
    

account_registri_period()

class progressivi_iva_period(osv.osv):
    _name = 'progressivi.iva.period'
    _description = ' Progressivi dei Registri Iva per periodo'
    
            
    """  si aggiornano quando si lancia la stampa del registro non importa lo azzera e lo ricalcola' """
    _columns = {
                'period_registro_id': fields.many2one('account.registri_period', 'Periodo Registro', required=True, select=True),                
                'codice_iva':fields.many2one('account.tax', 'Codice Iva', required=True, readonly=False),
                'totale_imponibile': fields.float('Imponibile Periodo', help='Totale Imponibile del Periodo ', digits_compute=dp.get_precision('Account')),
                'totale_imposta': fields.float('Imposta del Periodo', help='Totale Imposta del Periodo ', digits_compute=dp.get_precision('Account')),
                }
    
    
    
progressivi_iva_period()


class causcont(osv.osv):
   _name = "causcont"
   _description = "Causali Contabili"
   _order = 'name,descaus'
   
   def name_get(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['name','descaus'], context, load='_classic_write')
        return [(x['id'], (x['name'] and (x['name'] + ' - ') or '') + x['descaus']) \
                for x in reads]

   _columns={
             'name':fields.char('Codice Causale ', size=10, required=True),
             'descaus':fields.char('Descrizione Causale ', size=64, required=False),
             'journal_id': fields.many2one('account.journal', 'Libro Giornale', required=True),
             'flag_cliente':fields.boolean('Causale Cliente'),
             'flag_fornitore':fields.boolean('Causale Fornitore'),
             'tipo_registro':fields.selection([("VE", "Vendite"),
                                                ('AC', 'Acquisti'),
                                                ('CS', 'Corrispettivi Scorporo'),
                                                ('CV', 'Corrispettivi Ventilazione'),
                                                ('SO', 'Sospensione'),
                                                ('NR', 'Nessun Registro')],"Tipo Registro", required=True),
             'num_registro_iva':fields.integer('Numero Registro ', required=True),
             'tipo_documento':fields.selection([("FA", "Fattura"),
                                                ('FC', 'Fattura Corrispettivi'),
                                                ('CO', 'Corrispettivi Scorporo'),
                                                ('NC', 'Nota Credito'),
                                                ('FCEE', 'Fatt. CEE'),
                                                ('NCEE', 'NC CEE'),
                                                ('ZZ', 'No Documento')],"Tipo Documento"),    
             'conto_iva':fields.many2one('account.account', "Conto Iva"),
             'segno_conto_iva':fields.selection([("DA", "Dare"),
                                                ('AV', 'Avere'),
                                                ],"Segno"),
             'esigibilita':fields.selection([("NO", "Normale"),
                                                ('D132-95', 'Differita DL 132-95'),
                                                ('D313-97', 'Differita DL 313-97'),
                                                ('ID', 'Incasso Differita'),
                                                ('PD', 'Pagamento Differita'),
                                                ],"Esigibilità Iva"),
             'gg_differimento_iva':fields.integer('GG Differimento Iva ', required=False),
             'flag_ndoc':fields.selection([("O", "Obbligatorio"),
                                                ('F', 'Facoltativo'),
                                                ('N', 'Non Gestito'),
                                                ],"Test N° Doc"),
             'flag_ddoc':fields.selection([("O", "Obbligatorio"),
                                                ('F', 'Facoltativo'),
                                                ('N', 'Non Gestito'),
                                                ],"Test Data Doc"),
             'flag_partite':fields.selection([("C", "Crea Partite"),
                                                ('S', 'Salda Partite'),
                                                ('A', 'Non Gestito'),
                                                ('IP', 'Inc/Pag Contestuale'),
                                                ('N', 'Non Gestito'),
                                                ],"Flag Partite Aperte"),
             'flag_scadenze':fields.selection([("C", "Clienti"),
                                                ('F', 'Fornitori'),
                                                ('A', 'Non Gestito'),
                                                ('N', 'Non Gestito'),
                                                ],"Flag Tipo Scadenza"),
             'flag_apertura':fields.boolean('Causale di Apertura'),
             'flag_chiusura':fields.boolean('Causale di Chiusura'),
             'righe_cas_auto': fields.one2many('auto.causcont', 'causale', 'Righe Automatismi', required=True),
             
                      
             
             }



causcont() 


class auto_causcont_head(osv.osv):
   _name = "auto.causcont.head"
   _description = "Automatismi Causali Contabili Testa"
   _columns={
             'causale': fields.many2one('causcont', 'Causale', required=True, select=True),
             'name': fields.char('Name', size=64, required=True),
             'partner_id':fields.many2one('res.partner', 'Partner', required=False, select=True),
             'righe_auto': fields.one2many('auto.causcont.line', 'head', 'Righe Automatismi', required=True),
             

}

auto_causcont_head()


class auto_causcont_line(osv.osv):
   _name = "auto.causcont.line"
   _description = "Automatismi Causali Contabili righe"
   _order = 'head,sequence'
   _columns={
             'head':fields.many2one('auto.causcont.head', 'Automatismo', required=True, select=True),
             'sequence': fields.integer('Number', required=True),
             'type': fields.selection([('computed', 'Calcolato'),('input', 'User input')], 'Type', required=True),
             'python_code':fields.text('Python Code/Formula Calcolo'),             
             'conto': fields.many2one('account.account', 'Conto', required=True),
             'segno_riga':fields.selection([('DA','Dare'),('AV','Avere'),], 'Segno Riga', required=True),
             'tax_code_id': fields.many2one('account.tax', 'Codice Iva'),
             'flag_scorporo':fields.boolean('Scorporo',help="Se attivo l'iva sarà scacolata dal campo imponibile"),
             

}

auto_causcont_line()