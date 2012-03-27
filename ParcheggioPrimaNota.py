# -*- encoding: utf-8 -*- 

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import decimal_precision as dp
import time
import netsvc
import pooler, tools
import math
from tools.translate import _



class account_primanota(osv.osv):
    
    _name = 'account.primanota'
    _description = ' Prima Nota semplificata in stile Ad-Hoc Windows'
    _columns={
              'name': fields.char('Numero Registrazione', size=64, required=True,states={'posted':[('readonly',True)]}),
              'data_registrazione':fields.date('Data Registrazione', required=True, readonly=False, select=True,states={'posted':[('readonly',True)]}),
              'period_id': fields.many2one('account.period', 'Period', required=True, states={'posted':[('readonly',True)]}),
              'fiscalyear_id': fields.related('period_id', 'fiscalyear_id', string='Fiscal Year', type='many2one', relation='account.fiscalyear',states={'posted':[('readonly',True)]}),
              'state': fields.selection([('draft','Unposted'), ('posted','Posted')], 'State', required=True, readonly=True,
               help='All manually created new journal entry are usually in the state \'Unposted\', but you can set the option to skip that state on the related journal. In that case, they will be behave as journal entries automatically created by the system on document validation (invoices, bank statements...) and will be created in \'Posted\' state.'),
              'causale_id': fields.many2one('causcont', 'Causale', required=True, select=True,states={'posted':[('readonly',True)]}),
              'registro': fields.related('causale_id', 'tipo_registro', string='Registro', type='char', relation='causcont',states={'posted':[('readonly',True)]}),
              'num_registro': fields.related('causale_id', 'num_registro_iva', string='Num Registro', type='integer', relation='causcont',states={'posted':[('readonly',True)]}),
              'tipo_dcocumento': fields.related('causale_id', 'tipo_dcocumento', string='Tipo Documento', type='char', relation='causcont',states={'posted':[('readonly',True)]}),
              'numero_doc':fields.char('Numero Doc.',size=30,states={'posted':[('readonly',True)]}), ## fare il controllo di obbligatorietà legato al tipo di documento meglio se  come funzione nella constraint
              'data_doc':fields.date('Data Doc.', required=True, readonly=False, select=True,states={'posted':[('readonly',True)]}), ## fare il controllo di obbligatorietà legato al tipo di documento meglio se  come funzione nella constraint
              'protocollo':fields.integer('Protocollo'), ## anche qui controllare l'obbligatorietà e la sequenza del n° di protocollo
              'decrizione':field.text('Descrizione'),
              'currency_id': fields.many2one('res.currency', 'Valuta della Registrazione', help="Permette di gestire le operazioni in valuta estera NON ANCORA GESTITO"),
              'pnt_righe': fields.one2many('account.primanota_righe', 'name', 'Dettaglio Righe',  states={'posted':[('readonly',True)]}),
              }


    _defaults = {
             'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'primanota'), # RICORDATI DI CREARE UNA SEQUENZA ANNUALE PER QUESTA SEQUENZA
             }

account_primanota()

class account_primanota_righe(osv.osv):
    
    _name = 'account.primanota_righe'
    _description = ' Prima Nota Righe '
    _columns = {
                'name': fields.many2one('account.primanota', 'Testata Prima Nota', required=True, select=True),
                'conto_id':fields.many2one('account.account', "Conto",states={'posted':[('readonly',True)]},required=True ),
                'tipo_sottoconto':fields.related('conto_id', 'tipo_sottoconto', string='Tipo Conto', type='char', relation='account.account',states={'posted':[('readonly',True)]}),
                # tipo sottoconto mi dice se devo cercare un cliente o un fornitore o se si tratta di una riga iva questo serve sempre in tutti i conteggi e automatismi
                'partner_id': fields.many2one('res.partner', 'Cliente/Fornitore',  states={'posted':[('readonly',True)]}, required=True, select=True),
                'dare': fields.float('Dare', digits_compute=dp.get_precision('Account'), states={'posted':[('readonly',True)]}),
                'avere': fields.float('Avere', digits_compute=dp.get_precision('Account'), states={'posted':[('readonly',True)]}),
                'dessup': fields.char('Descrizione Riga', size=64, required=False),
                'codice_iva':fields.many2one('account.tax', 'Codice Iva', required=False, states={'posted':[('readonly',True)]}),
                'imponibile': fields.float('Imponibile', digits_compute=dp.get_precision('Account'), states={'posted':[('readonly',True)]}),
                'totdocumento': fields.float('totdocumento', digits_compute=dp.get_precision('Account'), states={'posted':[('readonly',True)]}), # quando è fattura o nota credito l'importo dare o avere va copiato in questo campo sulla riga cliente fornitore
                'pagamento_id':fields.many2one('account.payment.term', 'Pagamento', required=False, help="Necessario per le righe che aprono partite"),
                'causale':fields.related('name', 'causale_id', string='Causale di righa', type='many2one', relation='causcont',states={'posted':[('readonly',True)]}),
                 # 'causale2_id': fields.many2one('causcont', 'Causale di Riga', required=True, help="Utilizzabile per cambiare la descrizione sulla riga libro giornale",select=True,states={'posted':[('readonly',True)]}),
                 # HO DECISO CHE SI PUÒ USARE UNA SOLA CAUSALE PER REGISTRAZIONE POSSIAMO PENSARE A DEGLI AUTOMATISMI / WIZARD CHE FANNO INCASSO / PAGAMENTO CONTESTUALE
                }
    
account_primanota_righe()

class account_partite(osv.osv):
        _name = 'account.partite'
        _description = ' Prima Nota Partite Aperte e Chiuse '
        
        def _totale_partita(self, cr, uid, ids, field_name, arg, context=None):
            res = {}
            for partita in self.browse(cr, uid, ids, context=context):
                res[partita.id] = { 'totale_partita': 0}
                val = 0
                for line in partita.par_scadenze:
                    val += line.importo

                res[partita.id]['totale_partita'] = val
            return res

        def _totale_saldato(self, cr, uid, ids, field_name, arg, context=None):
            res = {}
            for partita in self.browse(cr, uid, ids, context=context):
                res[partita.id] = { 'totale_saldo': 0}
                val = 0
                for line in partita.par_scadenze:
                    val += line.saldato
                res[partita.id]['totale_saldo'] = val
            return res

        def _totale_da_saldare(self, cr, uid, ids, field_name, arg, context=None):
            res = {}
            for partita in self.browse(cr, uid, ids, context=context):
                res[partita.id]['totale_da_saldare'] = partita.totale_partita-partita.totale_saldo
            return res
       
        
        _columns = {
                    'name': fields.many2one('account.primanota_righe', 'Riga Prima Nota di Apertura', required=True, select=True),
                    'reg_pnt': fields.many2one('account.primanota', 'Testata Prima Nota di Apertura', required=True, select=True),
                    'num_reg': fields.related('reg_pnt', 'name', string='Numero Registrazione', type='char', relation='account.primanota'),
                    'data_reg': fields.related('reg_pnt', 'data_registrazione', string='Data Registrazione', type='datetime', relation='account.primanota'),
                    'num_reg': fields.related('reg_pnt', 'name', string='Numero Registrazione', type='char', relation='account.primanota'),
                    'tipo_dcocumento': fields.related('reg_pnt', 'tipo_dcocumento', string='Tipo Doc', type='char', relation='account.primanota'),
                    'numero_doc':fields.related('reg_pnt', 'numero_doc', string='Numero Doc', type='char', relation='account.primanota'),
                    'data_doc':fields.related('reg_pnt', 'data_doc', string='Numero Doc', type='char', relation='account.primanota'),
                    'partner_id': fields.many2one('res.partner', 'Cliente/Fornitore',  states={'posted':[('readonly',True)]}, required=True, select=True),
                    'totale_partita': fields.function(_totale_partita, method=True, digits_compute=dp.get_precision('Account'), string='Totale Partita', store=True, multi='sums'),# function
                    'totale_saldo': fields.function(_totale_saldato, method=True, digits_compute=dp.get_precision('Account'), string='Totale Saldato', store=True, multi='sums'),# function# function
                    'totale_da_saldare': fields.function(_totale_da_saldare, method=True, digits_compute=dp.get_precision('Account'), string='Totale da Saldare', store=True, multi='sums'),# function# function # function
                    'pagamento_id':fields.many2one('account.payment.term', 'Pagamento', required=False, help="Necessario per le righe che aprono partite"),
                    'par_scadenze': fields.one2many('account.partite_scadenze', 'name', 'Dettaglio Righe scadenze'),
                    }

    
account_primanota_partite()


class account_partite_scadenze(osv.osv):
        _name = 'account.partite_scadenze'
        _description = ' Prima Nota Partite Scadenze delle partite aperte '
        
        def _saldato(self, cr, uid, ids, field_name, arg, context=None):
            res = {}
            for partita in self.browse(cr, uid, ids, context=context):
                res[partita.id] = { 'saldato': 0}
                val = 0
                for line in partita.par_saldi:
                    val += line.saldo
                res[partita.id]['saldato'] = val
            return res
        
        
        
        
        def _da_saldare(self, cr, uid, ids, field_name, arg, context=None):
            res = {}
            for partita in self.browse(cr, uid, ids, context=context):
                res[partita.id]['da_saldare'] = partita.importo-partita.saldato
            return res
        
        _columns = {
                    'name': fields.many2one('account.partite', 'Testata Partita', required=True, select=True),
                    'data_scadenza':fields.date('Data Scadenza', required=True, readonly=False, select=True),
                    'importo': fields.float('Importo', digits_compute=dp.get_precision('Account'), help="Importo da Incassare o Pagare"),
                    'saldato': fields.function(_saldato, method=True, digits_compute=dp.get_precision('Account'), string='Saldato', store=True, multi='sums'),
                    'da_saldare':fields.function(_da_saldare, method=True, digits_compute=dp.get_precision('Account'), string='Da Saldare', store=True, multi='sums'),
                    'par_saldi': fields.one2many('account.partite_saldi', 'name', 'Dettaglio Righe Saldi'),
                    
                    }

account_partite_scadenze()



class account_partite_incassi(osv.osv):
        _name = 'account.partite_saldi'
        _description = ' Prima Nota Partite incassi e pagamenti  delle partite aperte '
        _columns = {
                    'name': fields.many2one('account.partite_scadenze', 'Riga Scadenza Partita', required=True, select=True),
                    'registrazione': fields.many2one('account.primanota_righe', 'Riga Prima Nota di Saldo', required=True, select=True),
                    'saldo': fields.float('saldo', digits_compute=dp.get_precision('Account'), help="Importo di saldo della riga"),                    
                    }

account_partite_scadenze()