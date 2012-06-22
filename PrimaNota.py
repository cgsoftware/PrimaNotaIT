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

def arrot(cr,uid,valore,decimali):
    #import pdb;pdb.set_trace()
    return round(valore,decimali(cr)[1])


class res_partner(osv.osv):
    _inherit = "account.move"
    _columns = {
                'contropartita_cliente':fields.many2one('account.account', "Contropartita Ricavo"),
                'contropartita_fornitore':fields.many2one('account.account', "Contropartita Costo"),
                
                }
# gfhfgd
res_partner()

class account_partite(osv.osv):
        _name = 'account.partite'
        _description = ' Prima Nota Partite Aperte e Chiuse '
        
        def _totali_partita(self, cr, uid, ids, field_name, arg, context=None):
            res = {}
            #import pdb;pdb.set_trace()
            if ids:
             for partita in self.browse(cr, uid, ids, context=context):       
                res[partita.id] = { 'totale_partita': 0,'totale_saldo': 0,'totale_da_saldare': 0}
                totale_partita = 0
                totale_saldo=0
                for line in partita.par_scadenze:
                    totale_partita += line.importo
                    totale_saldo += line.saldato
                res[partita.id]['totale_partita'] = totale_partita
                res[partita.id]['totale_saldo'] = totale_saldo
                res[partita.id]['totale_da_saldare'] = res[partita.id]['totale_partita']-res[partita.id]['totale_saldo']
            return res


       
        
        _columns = {
                    'name': fields.char('Numero Partita', size=30, required=True, readonly=False, select=True),
                    'riga_reg_pnt': fields.many2one('account.move.line', 'Riga Prima Nota di Apertura', required=True, select=True),
                    'reg_pnt': fields.many2one('account.move', 'Testata Prima Nota di Apertura', required=True, select=True),
                    'num_reg': fields.related('reg_pnt', 'ref', string='Numero Registrazione', type='char',size=64, relation='account.move'),
                    'data_reg': fields.related('reg_pnt', 'date', string='Data Registrazione', type='date', relation='account.move'),
                    'causale_id':fields.related('reg_pnt', 'causale_id', string='Causale di riga', type='many2one', relation='causcont'),
                    # 'num_reg': fields.related('reg_pnt', 'number', string='Numero Registrazione', type='char', relation='account.primanota'),
                    'flag_saldata':fields.boolean('Saldata', required=False), # per comodità di gestioni future aggiunto il flag saldata TO DO
                    'tipo_documento': fields.related('reg_pnt', 'tipo_documento', string='Tipo Doc', type='char' ,size=64, relation='account.move'),
                    'numero_doc':fields.related('reg_pnt', 'numero_doc', string='Numero Doc', type='char',size=64, relation='account.move'),
                    'data_doc':fields.related('reg_pnt', 'data_doc', string='Data Doc', type='date', relation='account.move'),
                    'partner_id': fields.many2one('res.partner', 'Cliente/Fornitore',  states={'posted':[('readonly',True)]}, required=True, select=True),
                    'totale_partita':fields.function(_totali_partita, method=True, digits_compute=dp.get_precision('Account'), string='Totale Partita', store=False, multi='sums'),                
                    'totale_saldo': fields.function(_totali_partita, method=True, digits_compute=dp.get_precision('Account'), string='Totale Saldato', store=False, multi='sums'),
                    'totale_da_saldare': fields.function(_totali_partita, method=True, digits_compute=dp.get_precision('Account'), string='Totale da Saldare', store=False, multi='sums'),
                    'pagamento_id':fields.many2one('account.payment.term', 'Pagamento', required=False, help="Necessario per le righe che aprono partite"),
                    'par_scadenze': fields.one2many('account.partite_scadenze', 'name', 'Dettaglio Righe scadenze'),
                                    
                    }

        _defaults = {
                 'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'partite'),                
                 }
        
        def onchange_riga(self,cr,uid,ids,riga_reg_pnt,context):
            v={}
            domain={}
            warning={}
            if riga_reg_pnt:
                riga_reg= self.pool.get('account.move.line').browse(cr,uid,riga_reg_pnt,context)
                v['reg_pnt'] = riga_reg.move_id.id
                v['num_reg'] = riga_reg.name
                v['data_reg'] = riga_reg.date
                v['tipo_documento'] = riga_reg.move_id.tipo_documento
                v['numero_doc'] = riga_reg.move_id.numero_doc
                v['data_doc'] = riga_reg.move_id.data_doc
                v['partner_id'] = riga_reg.partner_id.id
                v['pagamento_id'] = riga_reg.pagamento_id.id
            return  {'value':v,'domain':domain,'warning':warning} 
        
        def unlink(self, cr, uid, ids, context=None, check=True):
            if context is None:
                context = {}
            if ids:
                #import pdb;pdb.set_trace()
                par_obj = self.browse(cr,uid,ids,context)[0]
                move_id = par_obj.riga_reg_pnt.id 
                ok = self.pool.get('account.move.line').write(cr,uid,[move_id],{'partita_id':False,'par_saldi':False})             
            result = super(account_partite, self).unlink(cr, uid, ids, context=context)
            
            
            return result
account_partite()


class account_partite_scadenze(osv.osv):
        _name = 'account.partite_scadenze'
        _description = ' Prima Nota Partite Scadenze delle partite aperte '
        
        def _totali_saldato(self, cr, uid, ids, field_name, arg, context=None):
            res = {}
            for partita in self.browse(cr, uid, ids, context=context):
                res[partita.id] = { 'saldato': 0,'da_saldare': 0}
                val = 0
                for line in partita.par_saldi:
                    val += line.saldo
                res[partita.id]['saldato'] = val
                res[partita.id]['da_saldare'] = partita.importo-res[partita.id]['saldato']
            return res
        

        
        _columns = {
                    'name': fields.many2one('account.partite', 'Testata Partita',ondelete='cascade', required=True, select=True),                            
                    'data_scadenza':fields.date('Data Scadenza', required=True, readonly=False, select=True),
                    'importo': fields.float('Importo', digits_compute=dp.get_precision('Account'), help="Importo da Incassare o Pagare"),
                    'saldato': fields.function(_totali_saldato, method=True, digits_compute=dp.get_precision('Account'), string='Saldato', store=False, multi='sums'),
                    'da_saldare':fields.function(_totali_saldato, method=True, digits_compute=dp.get_precision('Account'), string='Da Saldare', store=False, multi='sums'),
                    'par_saldi': fields.one2many('account.partite_saldi', 'name', 'Dettaglio Righe Saldi'),
                    'flag_saldata':fields.boolean('Saldata', required=False), # per comodità di gestioni future aggiunto il flag saldata da gestire TO Do
                    
                    }

account_partite_scadenze()



class account_partite_incassi(osv.osv):
        _name = 'account.partite_saldi'
        _description = ' Prima Nota Partite incassi e pagamenti  delle partite aperte '
        _columns = {
                    'name': fields.many2one('account.partite_scadenze', 'Riga Scadenza Partita'),
                    'registrazione': fields.many2one('account.move.line', 'Riga Prima Nota di Saldo'),
                    'saldo': fields.float('saldo', digits_compute=dp.get_precision('Account'), help="Importo di saldo della riga"),                    
                    }

account_partite_incassi()


class account_move(osv.osv):
    _inherit = "account.move"
    
    
    def _get_datareg(self, cr, uid, context=None):
        id = self.search(cr, uid,[],order='id desc')
        if id:
            #import pdb;pdb.set_trace()
            return self.browse(cr,uid,[id[len(id)-1]])[0].date
        else:
            return  time.strftime('%Y-%m-%d')
        return False
    
    def _get_period(self, cr, uid, context=None):
        dt = self._get_datareg(cr, uid, context)
        periods = self.pool.get('account.period').find(cr, uid,dt=dt)
        if periods:
            return periods[0]
        return False
    
    
    _columns={
              # 'partner_id': fields.many2one('res.partner', 'Cliente/Fornitore',   required=False, select=True),
              'pagamento_id':fields.many2one('account.payment.term', 'Pagamento', required=False, help="Necessario per le righe che aprono partite"),
              'fiscalyear_id': fields.related('period_id', 'fiscalyear_id', string='Fiscal Year', type='many2one', relation='account.fiscalyear',states={'posted':[('readonly',True)]}),
              'causale_id': fields.many2one('causcont', 'Causale', required=True, select=True,states={'posted':[('readonly',True)]}),
              'registro': fields.related('causale_id', 'tipo_registro', string='Registro', type='char', relation='causcont',states={'posted':[('readonly',True)]}),
              'flag_ndoc': fields.related('causale_id', 'flag_ndoc', string='ndoc', type='char', relation='causcont',states={'posted':[('readonly',True)]}),
              'flag_ddoc': fields.related('causale_id', 'flag_ddoc', string='ddoc', type='char', relation='causcont',states={'posted':[('readonly',True)]}),
              'flag_partite': fields.related('causale_id', 'flag_partite', string='flag_partite', type='char', relation='causcont',states={'posted':[('readonly',True)]}),              
              'flag_scadenze': fields.related('causale_id', 'flag_scadenze', string='flag_scadenze', type='char', relation='causcont',states={'posted':[('readonly',True)]}),
              'flag_apertura': fields.related('causale_id', 'flag_apertura', string='flag_apertura', type='boolean', relation='causcont',states={'posted':[('readonly',True)]}),
              'flag_chiusura': fields.related('causale_id', 'flag_chiusura', string='flag_chiusura', type='boolean', relation='causcont',states={'posted':[('readonly',True)]}),
              'flag_cliente': fields.related('causale_id', 'flag_cliente', string='flag_cliente', type='boolean', relation='causcont',states={'posted':[('readonly',True)]}),
              'flag_fornitore': fields.related('causale_id', 'flag_fornitore', string='flag_fornitore', type='boolean', relation='causcont',states={'posted':[('readonly',True)]}),                                          
              'num_registro': fields.related('causale_id', 'num_registro_iva', string='Num Registro', type='integer', relation='causcont',states={'posted':[('readonly',True)]}),
              'tipo_documento': fields.related('causale_id', 'tipo_documento', string='Tipo Documento', type='char', relation='causcont',states={'posted':[('readonly',True)]}),
              'numero_doc':fields.char('Numero Doc.',size=30,states={'posted':[('readonly',True)]}), ## fare il controllo di obbligatorietà legato al tipo di documento meglio se  come funzione nella constraint
              'data_doc':fields.date('Data Doc.', required=False, readonly=False, select=True,states={'posted':[('readonly',True)]}), ## fare il controllo di obbligatorietà legato al tipo di documento meglio se  come funzione nella constraint
              'protocollo':fields.integer('Protocollo', states={'posted':[('readonly',True)]}), ## anche qui controllare l'obbligatorietà e la sequenza del n° di protocollo
              
              }
    
    _defaults = {
             'date': _get_datareg,
             'period_id': _get_period,
             }    
    
    def check_protocollo(self,cr,uid,ids,causale_id,period_id,date,check,proto,context):
        protocollo = 0
        prot_obj = self.pool.get('account.fiscalyear.protocolli')
        if period_id:
            fiscalyear_id = self.pool.get('account.period').browse(cr,uid,period_id,context).fiscalyear_id.id
        else:
            fiscalyear_id=False
        if causale_id:
            causale = self.pool.get('causcont').browse(cr,uid,causale_id)
            if causale.tipo_registro!='NR':
                # è un registro iva
                cerca = [('fiscalyear_id','=',fiscalyear_id),('tipo_registro','=',causale.tipo_registro),('num_registro_iva','=',causale.num_registro_iva)]
                #import pdb;pdb.set_trace()
                ids_prot = prot_obj.search(cr,uid,cerca)
                if ids_prot:
                    rg_prot = prot_obj.browse(cr,uid,ids_prot[0])
                    if check: # solo controllo
                     if rg_prot.data_registrazione>date:
                        raise osv.except_osv(_('Errore !'), _('Data Registrazione Inferiore a Data Ultimo protocollo'))
                     else:
                        protocollo = 1 + rg_prot.protocollo
                    else:
                        # deve aggiornare il num. di protocollo se è il caso
                        if rg_prot.protocollo<proto: 
                            # deve aggrionare altrimenti è ok
                            if rg_prot.data_registrazione>date:
                                   raise osv.except_osv(_('Errore !'), _('Data Registrazione Inferiore a Data Ultimo protocollo'))
                                   return False
                            else:
                                return prot_obj.write(cr,uid,ids_prot,{'protocollo':proto,'data_registrazione':date})
                        else:
                            return True
                else:
                    rg_prot= {
                             'fiscalyear_id':fiscalyear_id,
                             'tipo_registro':causale.tipo_registro,
                             'num_registro_iva':causale.num_registro_iva,
                             'protocollo':0,
                             'data_registrazione':date,
                             }
                    ids_prot = prot_obj.create(cr,uid,rg_prot,context)
                    protocollo = 1
                    
                        
        return protocollo
    
    def onchange_date(self,cr,uid,ids,date,context):
        res ={}        
        if date:
            periods = self.pool.get('account.period').find(cr, uid,dt=date)
            if periods:
                res['period_id']= periods[0]

        return  {'value':res}
    
    def onchange_causale_id(self,cr,uid,ids,causale_id,period_id,date,context):
        res ={}        
        if causale_id:
            causale = self.pool.get('causcont').browse(cr,uid,causale_id)
            res['journal_id'] = causale.journal_id.id
            res['registro']= causale.tipo_registro
            res['num_registro']= causale.num_registro_iva
            res['tipo_documento']= causale.tipo_documento
            res['ref']= causale.descaus
            res["flag_ndoc"]= causale.flag_ndoc
            res["flag_ddoc"]= causale.flag_ddoc
            res["flag_partite"]= causale.flag_partite
            res["flag_scadenze"]= causale.flag_scadenze
            res["flag_apertura"]= causale.flag_apertura
            res["flag_chiusura"]= causale.flag_chiusura
            res["flag_cliente"]= causale.flag_cliente
            res["flag_fornitore"]= causale.flag_fornitore
            res["protocollo"]=self.check_protocollo(cr, uid, ids, causale_id, period_id, date,True,0, context)
           
        #import pdb;pdb.set_trace()
        return  {'value':res}
    
    def check_partite(self,cr,uid,ids,context=False):        
        res = False
        if ids:
            for move in self.browse(cr,uid,ids):                             
                if move.flag_partite=='C':
                    #deve creare una partita                 
                    for move_line in move.line_id:                       
                       conto = False
                     #  import pdb;pdb.set_trace()
                       if (not move_line.partita_id) and (not move_line.par_saldi):
                        if move.flag_cliente:
                            if move_line.partner_id.property_account_receivable:
                                conto = move_line.partner_id.property_account_receivable.id
                            else:
                                raise osv.except_osv(_('Errore !'), _('Partita Non Creata Per assenza del Pagamento sulla riga del Partner ' + move_line.partner_id.ref ))
                        if move.flag_fornitore:
                            conto = move_line.partner_id.property_account_payable.id
                        if conto == move_line.account_id.id:
                            # è la riga del cliente
                            if move_line.pagamento_id:
                                importo = float(abs(move_line.credit-move_line.debit))
                                testa = {
                                         'riga_reg_pnt':move_line.id,
                                         'reg_pnt':move.id,
                                         'num_reg': move.ref,
                                         'data_reg': move.date,
                                         'tipo_documento': move.tipo_documento,
                                         'numero_doc':move.numero_doc,
                                         'data_doc':move.data_doc,
                                         'partner_id': move_line.partner_id.id,
                                         'pagamento_id':move_line.pagamento_id.id,
                                         'totale_partita':arrot(cr,uid,importo,dp.get_precision('Account')),
                                         }
                                id_testa_par = self.pool.get('account.partite').create(cr,uid,testa)                           
                                scadenze = self.pool.get('account.payment.term').compute(cr, uid, move_line.pagamento_id.id,importo, move.data_doc, context)
                                if scadenze:
                                    for scadenza in scadenze:
                                        riga_scad = {
                                                     'name':id_testa_par,                                                     
                                                     'data_scadenza':scadenza[0],
                                                     'importo':arrot(cr,uid,scadenza[1],dp.get_precision('Account')),
                                                     }
                                        res = self.pool.get('account.partite_scadenze').create(cr, uid, riga_scad)
                                #import pdb;pdb.set_trace()
                                ok = self.pool.get('account.partite').write(cr,uid,id_testa_par,testa)
                                ok = self.pool.get('account.move.line').write(cr,uid,[move_line.id],{'partita_id':id_testa_par})        
                            else:
                                raise osv.except_osv(_('Errore !'), _('Partita Non Creata Per assenza del Pagamento sulla riga del Partner'))
                                            
                if move.flag_partite=='S':
                    # TO DO deve lanciare un wizard per saldare ci proviamo a lanciare una action e vediamo
                            #import pdb;pdb.set_trace()
                            #raise osv.except_osv(_('Errore !'), _('Non è Possibile Saldare le Partite Collegate Usare la Funzione SaldaConto'))
                            #return True
                            pass
#                            return {
#                                    'name': 'Saldaconto Partner',
#                                    'view_type': 'form',
#                                    'view_mode': 'form',
#                                    'res_model': 'salda.partite',
#                                    'type': 'ir.actions.act_window',
#                                    'target': 'new',
#                                    'context': context
#                                    }
        return res
    
    def button_validate(self, cursor, user, ids, context=None):
       cr = cursor
       uid = user
       result= False
       if ids: 
        result = super(account_move, self).button_validate(cr, uid, ids, context)
        #import pdb;pdb.set_trace()
        if result:
            pass
            result = self.check_partite(cr,uid,ids,context)
            #import pdb;pdb.set_trace()
        return result
    
    def button_cancel(self, cr, uid, ids, context=None):

        
        result = super(account_move, self).button_cancel(cr, uid, ids, context)
        
        return True

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        result = super(account_move, self).create(cr, uid, vals, context)
        if result:
           if vals.get('period_id',False):
            causale = self.pool.get('causcont').browse(cr,uid, vals['causale_id'])
            if causale.tipo_registro!='NR':
                #import pdb;pdb.set_trace()
                ok_prot = self.check_protocollo(cr, uid, [result], vals['causale_id'], vals['period_id'], vals['date'],False,vals['protocollo'], context)
                if not ok_prot:
                    result = False
        return result
    


account_move()



class account_move_line(osv.osv):
    _inherit = "account.move.line"
    _columns = {
                'tipo_sottoconto':fields.related('conto_id', 'tipo_sottoconto', string='Tipo Conto', type='char', relation='account.account',states={'posted':[('readonly',True)]}),
                'imponibile': fields.float('Imponibile', digits_compute=dp.get_precision('Account'), states={'posted':[('readonly',True)]}),
                'totdocumento': fields.float('totdocumento', digits_compute=dp.get_precision('Account'), states={'posted':[('readonly',True)]}), # quando è fattura o nota credito l'importo dare o avere va copiato in questo campo sulla riga cliente fornitore
                'pagamento_id':fields.many2one('account.payment.term', 'Pagamento', required=False, help="Necessario per le righe che aprono partite"),
                'causale_id':fields.related('move_id', 'causale_id', string='Causale di riga', type='many2one', relation='causcont',states={'posted':[('readonly',True)]}),
                'partita_id':fields.many2one('account.partite', 'Partita di Aperta',ondelete="set default", required=False, help="Necessario per le righe che aprono partite"),
                'par_saldi': fields.one2many('account.partite_saldi', 'registrazione', 'Dettaglio Righe Saldi'),
                }
    
    _defaults={
               'partita_id':False,
               'par_saldi':False,
               }
    
    def crea_righe_calcoli(self,lines):
        risultati = {}
        i=0
        #import pdb;pdb.set_trace()
        if lines:
          lines.reverse()
          for riga in lines:
            i+=1
            risultati[i]=abs(riga[2]['credit']-riga[2]['debit'])
        return risultati
    
    def default_get(self, cr, uid, fields, context=None):
        #import pdb;pdb.set_trace()
        data = super(account_move_line, self).default_get(cr, uid, fields, context=context)
        data['name']=context.get('ref')
        data['ref']=context.get('ref')
        data['partner_id']=context.get('partner_id')
        data['causale_id']=context.get('causale_id')
        data['journal_id']=context.get('journal_id')
        
        if context.get('causale_id'):
            # cercherò l'automatismo di causale base in questo caso se 
            causale = self.pool.get('causcont').browse(cr,uid,context.get('causale_id'))
            id_auto = self.pool.get('auto.causcont.head').search(cr,uid,[('causale','=',causale.id),('partner_id','=',context.get('partner_id'))])
            if not id_auto:
                # non hai trovato un automatismo del partner
                id_auto = self.pool.get('auto.causcont.head').search(cr,uid,[('causale','=',causale.id),('partner_id','=',None)])
            if id_auto:
                # non c'è un automatismo della causale seguirà
                #import pdb;pdb.set_trace()
                righe_auto_ids = self.pool.get('auto.causcont.line').search(cr,uid,[('head','=',id_auto[0])],order='sequence')
                righe_auto = self.pool.get('auto.causcont.line').browse(cr,uid,righe_auto_ids)
                
                riga = len(context.get('lines'))
                #import pdb;pdb.set_trace()
                if riga<=len(righe_auto)-1:
                    # ha qualcosa da calcolare solo se non si è superato il numero di righe dell'automatismo FORSE UN DOMANI SERVITÀ UN NUMERATORE PER AVERE UNIVOCITÀ
                    data['account_id']=righe_auto[riga].conto.id
                    
                    data['credit']=0
                    data['debit']=0  
                    #import pdb;pdb.set_trace()
                    if righe_auto[riga].type=='computed':
                        # è un campo calcolato in base a valori precedentemente inseriti
                        #import pdb;pdb.set_trace()
                        righe_val_ins = self.crea_righe_calcoli(context.get('lines'))
                        if righe_val_ins:
                            
                            #righe_val_ins= righe_val_ins.reverse()
                            importo = eval(righe_auto[riga].python_code.replace('L','righe_val_ins'))  # è un importo calcolato sulle righe precedenti
                        if righe_auto[riga].tax_code_id:
                            # ora deve riportare l'importo su imponibile e di conseguenca calcolare l'imposta e matterla al lato giusto
                            data['imponibile']=importo
                            data['account_tax_id']=righe_auto[riga].tax_code_id.id
                            if righe_auto[riga].flag_scorporo:
                                # deve scorpoprare l'iva
                                imposta = importo-(importo / (1+righe_auto[riga].tax_code_id.amount))
                                imponibile = importo - imposta
                                data['imponibile']=imponibile                                
                            else:
                                imposta = importo * righe_auto[riga].tax_code_id.amount
                                imponibile = importo 
                                data['imponibile']=imponibile
                            #import pdb;pdb.set_trace()
                            if righe_auto[riga].segno_riga=="DA":
                                #segno dare
                                data['credit']=0
                                data['debit']=imposta       
                            else:
                                #segno dare
                                data['credit']=imposta
                                data['debit']=0       
                                 
                        else:
                            data['imponibile']=0 
                            if righe_auto[riga].segno_riga=="DA":
                                #segno dare
                                data['credit']=0
                                data['debit']=importo       
                            else:
                                #segno dare
                                data['credit']=importo       
                                data['debit']=0
                                                         
                      
                    
            else:
              # non c'è un automatismo della causale seguirà regole standard      
              pass
        
        return data

    
    def _default_get(self, cr, uid, fields, context=None):
        data = super(account_move_line, self)._default_get(cr, uid, fields, context=context)
        #import pdb;pdb.set_trace()
        return data

    def onchange_imponibile(self, cr, uid, ids, causale_id, partner_id,account_tax_id, imponibile,account_id=None, debit=0, credit=0, date=False, journal=False):
        warning= {}
        val={}
        if account_tax_id and causale_id:
            tax = self.pool.get('account.tax').browse(cr,uid,account_tax_id)
            imposta = imponibile*tax.amount
            causale =  self.pool.get('causcont').browse(cr,uid,causale_id)
            if causale.segno_conto_iva=='DA':
               #segno dare
                val['credit']=0
                val['debit']=imposta       
            else:
                 #segno dare
                 val['credit']=imposta
                 val['debit']=0       
        else:
          #  warning = {
          #             'title': 'ATTENZIONE !',
          #              'message':'Campo Utilizzabile solo per Righe Iva ',                                   
          #                          }
            val['imponibile']=0
            
        return {'value':val,'warning':warning}   
    
    def onchange_partner_id(self, cr, uid, ids, move_id, partner_id, account_id=None, debit=0, credit=0, date=False, journal=False):    
        res = super(account_move_line,self).onchange_partner_id(cr, uid, ids, move_id, partner_id, account_id, debit, credit, date, journal)
        if res:
            val = res.get('value',False)
            if partner_id:
                part = self.pool.get('res.partner').browse(cr, uid, partner_id)
                if part.property_payment_term:
                    val['pagamento_id']= part.property_payment_term.id
        return {'value':val}
    
    def unlink(self, cr, uid, ids, context=None, check=True):
        if context is None:
            context = {}    
        result = False    
        #import pdb;pdb.set_trace()
        for riga_reg in self.browse(cr,uid,ids):
          if riga_reg.partita_id:
            # for riga_par in riga_reg.partita_id:
                ok = self.pool.get('account.partite').unlink(cr,uid,[riga_reg.partita_id.id])
          if riga_reg.par_saldi:
            for riga_par in riga_reg.par_saldi:
                ok = self.pool.get('account.partite_saldi').unlink(cr,uid,[riga_par.id])  
          
          
        result = super(account_move_line,self).unlink(cr,uid,ids,context)
        return result
    
    
account_move_line()
