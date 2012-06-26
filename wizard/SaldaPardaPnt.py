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

class salda_partite(osv.osv_memory):
    _name = 'salda.partite'
    _description = 'Wizard di Salda Partite '
    _columns = {
                'date': fields.date('Date', required=True),
                'partner_id': fields.many2one('res.partner', 'Cliente/Fornitore', required=True),
                'importo_oper': fields.float('Importo Operazione', digits_compute=dp.get_precision('Account'),readonly=False, help="Importo Operazione"),
                'importo_resi': fields.float('Importo Residuo', digits_compute=dp.get_precision('Account'),readonly=False  , help="Importo Residuo"),
                'causale_id': fields.many2one('causcont', 'Causale', required=True),
                'account_id': fields.many2one('account.account', 'Conto Finanziario', required=True),
                'segno_riga':fields.selection([('DA','Dare'),('AV','Avere'),], 'Segno', required=True),
                'ref': fields.char('Reference', size=64),
                'narration':fields.text('Descrizione'),
                'par_scadenze': fields.one2many('salda.partite.righe', 'testa_saldaconto', 'Scadenze da Saldare'),
                }
    
    _defaults = {
                 'date': lambda *a: time.strftime('%Y-%m-%d'),
                }
    
    def onchange_causale_id(self,cr,uid,ids,causale_id,partner_id,context=None):
        #import pdb;pdb.set_trace()
        res ={}        
        if not context:
            context={}
        if causale_id:
            causale = self.pool.get('causcont').browse(cr,uid,causale_id)
            res['ref']= causale.descaus
            cerca = [('causale','=',causale_id),('partner_id','=',partner_id)]
            ids_auto = self.pool.get('auto.causcont.head').search(cr,uid,cerca)
            if ids_auto and len(ids_auto)==1:
                # Ha trovato una causale per il partner se è + di uno c'è casino e usa lo standard
                pass
            else:
                cerca = [('causale','=',causale_id),('partner_id','=',False)]
                ids_auto = self.pool.get('auto.causcont.head').search(cr,uid,cerca)
            if ids_auto:
                # Un automatismo è trovato ora legge le righe
                testa_auto = self.pool.get('auto.causcont.head').browse(cr,uid,ids_auto[0],context)
                partner_obj = self.pool.get('res.partner').browse(cr,uid,partner_id,context)
                #import pdb;pdb.set_trace()
                for riga_auto in testa_auto.righe_auto:
                    # cerca il conto finanziario
                    if (riga_auto.conto.id != partner_obj.property_account_receivable.id and riga_auto.conto.id != partner_obj.property_account_payable.id ):
                        # è una riga diversa da quella del conto cliente/fornitore e prende questa
                        res['account_id']= riga_auto.conto.id
                        res ['segno_riga']= riga_auto.segno_riga
                  
           
        #import pdb;pdb.set_trace()
        return  {'value':res}

    def onchange_partner_id(self,cr,uid,ids,partner_id,context=None):
        #import pdb;pdb.set_trace()       
        res ={}   
        domain={}
        warning={}        
        if not context:
            context={}
        return  {'value':res,'domain':domain,'warning':warning}

    def check(self, cr, uid, ids, context=None):
        #import pdb;pdb.set_trace()
        if ids:
            totale_residuo = 0
            # questo calcolo vale solo per partner dello stesso segno dell'operazione
            for testa in self.browse(cr,uid,ids):
                totale_residuo = testa.importo_oper
                for riga in testa.par_scadenze:
                    if not (riga.tipo_documento) or 'F' in riga.tipo_documento  or riga.tipo_documento == 'ZZ':
                        totale_residuo-= riga.saldatt
                    else:
                        totale_residuo+= riga.saldatt
                self.write(cr,uid,[testa.id],{'importo_resi':totale_residuo})
        return True
                
    def prepara(self, cr, uid, ids, context=None):
        if ids:
         testa = self.browse(cr,uid,ids,context)[0] 
         testa.causale_id        
         if testa.partner_id:
            for riga in testa.par_scadenze:
                ok = self.pool.get('salda.partite.righe').unlink(cr,uid,[riga.id],context)            
            cerca = [('partner_id','=',testa.partner_id.id),('totale_da_saldare','!=',0)]
            ids_partite = self.pool.get('account.partite').search(cr,uid,cerca)
            if ids_partite:
                scad_riga={}
                for testapar in self.pool.get('account.partite').browse(cr,uid,ids_partite,context):
                  # prende solo le causali coerenti con quella della regsitrazione, se si tratta di cliente prende solo le fatture e le nc cliente
                  # in pratica si impedisce la registrazione di compensazione diretta cliente fornitore
                  if  testa.causale_id.flag_cliente == testapar.causale_id.flag_cliente and testa.causale_id.flag_fornitore == testapar.causale_id.flag_fornitore:
                    for scadenza in testapar.par_scadenze:
                        if scadenza.da_saldare<>0:
                            # il segno meno per permettere le compensazioni tra clienti e fronitori e delle note di credito
                           # if testapar.causale_id.flag_cliente and testapar.causale_id.tipo_documento in ['FA','FCEE','FC']:
                            importo = scadenza.importo * 1
                            da_saldare = scadenza.da_saldare * 1
                            #if testapar.causale_id.flag_cliente and testapar.causale_id.tipo_documento in ['NC','NCEE']:
                            #    importo = scadenza.importo * -1
                            #    da_saldare = scadenza.da_saldare * -1
                            #if testapar.causale_id.flag_fornitore and testapar.causale_id.tipo_documento in ['FA','FCEE','FC']:
                            #    importo = scadenza.importo * -1
                            #    da_saldare = scadenza.da_saldare * -1
                            #if testapar.causale_id.flag_fornitore and testapar.causale_id.tipo_documento in ['NC','NCEE']:
                            #    importo = scadenza.importo * 1
                            #    da_saldare = scadenza.da_saldare * 1                                
                            scad_riga=   {
                                                'testa_saldaconto':testa.id,
                                                'scadenza_id':scadenza.id,
                                                'data_scadenza':scadenza.data_scadenza,
                                                'importo':importo,
                                                'da_saldare':da_saldare,
                                                'flg_salda':False,
                                                'saldatt':0.0,
                                                'numero_doc':testapar.numero_doc,
                                                'data_doc':testapar.data_doc,
                                                'protocollo':testapar.reg_pnt.protocollo,
                                                'tipo_documento':testapar.causale_id.tipo_documento,
                                                }
                            id_riga = self.pool.get('salda.partite.righe').create(cr,uid,scad_riga,context)                                                                                                                          
            else:
                    warning = {
                                    'title': 'ATTENZIONE !',
                                    'message':'Non ci sono Partite Aperte',
                                }
            
        #import pdb;pdb.set_trace()
        return True
        
    def onchange_importo_oper(self,cr,uid,ids,importo_oper,partner_id,context):
        #import pdb;pdb.set_trace()
        res ={}   
        domain={}
        warning={}        
        if not context:
            context={}
        if ids:
            testa = self.browse(cr,uid,ids,context)[0]
            for riga in testa.par_scadenze:
                ok = self.pool.get('salda.partite.righe').unlink(cr,uid,[riga.id],context)
                ok = self.prepara(cr, uid, ids, context)
        res['importo_resi']= importo_oper
        return  {'value':res,'domain':domain,'warning':warning}

           
    def salda_conti(self,cr,uid,ids,context):
        # per il momento non tiene conto degli abbuoni attivi e passivi
        
        if ids:
           # per prima cosa scrive la registrazione 
           testa = self.browse(cr,uid,ids,context)[0]          
           regi = {
                                  'partner_id':testa.partner_id.id,
                                  'date':testa.date,
                                  'narration':testa.narration,
                                  'ref':testa.ref,
                                  'state':'draft',
                                  'causale_id':testa.causale_id.id,
                                  }
           res = self.pool.get('account.move').onchange_date(cr,uid,ids,testa.date,context)
           period_id = res.get('value',False)
           re = self.pool.get('account.move').onchange_causale_id(cr,uid,ids,testa.causale_id.id,period_id['period_id'],testa.date,context)
           regi.update(re.get('value',False))
           regi.update(period_id)
           #import pdb;pdb.set_trace()
           id_reg = self.pool.get('account.move').create(cr,uid,regi,context)
        if id_reg:
           elenco_righe = []
           riga={}
           if testa.causale_id.flag_fornitore:
               conto = testa.partner_id.property_account_payable.id
           if testa.causale_id.flag_cliente:
               conto = testa.partner_id.property_account_receivable.id
           if testa.segno_riga == 'DA':
               segno = 'AV'
           else:
               segno = 'DA'
           riga['account_id']= conto
           if segno =="DA":
               riga['debit']=testa.importo_oper
               riga['credit']=0.0
           else:
               riga['debit']=0.0
               riga['credit']=testa.importo_oper
           riga['partner_id']=testa.partner_id.id
           riga['state']='draft'
           riga['move_id']= id_reg
           riga['name']=testa.ref
           id_riga = self.pool.get('account.move.line').create(cr,uid,riga,context)

           riga={}
           riga['account_id']= testa.account_id.id
           if testa.segno_riga =="DA":
               riga['debit']=testa.importo_oper
               riga['credit']=0.0
           else:
               riga['debit']=0.0
               riga['credit']=testa.importo_oper
           riga['partner_id']=testa.partner_id.id
           riga['state']='draft'
           riga['move_id']= id_reg
           riga['name']=testa.ref
           id_riga = self.pool.get('account.move.line').create(cr,uid,riga,context)
           #import pdb;pdb.set_trace()
           
           if id_reg:
               #ora cerco l'id del mastro cliente fornitore
               reg_obj = self.pool.get('account.move').browse(cr,uid,id_reg,context)
               for move_line in reg_obj.line_id:
                   if conto == move_line.account_id.id:
                       #trovato 
                       id_move_line = move_line.id
               for riga_scad in testa.par_scadenze:
                    rig_inc = {
                               'name':riga_scad.scadenza_id.id,
                               'registrazione':id_move_line,
                               'saldo':riga_scad.saldatt,
                               }
                    id_inc = self.pool.get('account.partite_saldi').create(cr,uid,rig_inc,context)
                    res = self.pool.get('account.partite_scadenze')._totali_saldato(cr,uid,[riga_scad.scadenza_id.id],'totale_da_saldare',[],context)
                    vals = res[riga_scad.scadenza_id.id]
                    ok = self.pool.get('account.partite_scadenze').write(cr,uid,[riga_scad.scadenza_id.id],vals)
                    #import pdb;pdb.set_trace()
                    res = self.pool.get('account.partite')._totali_partita(cr, uid, [riga_scad.scadenza_id.name.id], 'totale_da_saldare', [], context=None)
                    vals= res[riga_scad.scadenza_id.name.id]
                    ok = self.pool.get('account.partite').write(cr,uid,[riga_scad.scadenza_id.name.id],vals)
                    #import pdb;pdb.set_trace()
               ok = self.pool.get('account.move').post(cr,uid,[id_reg],context) 
                    

        return{
            'name': _('Salda Conto'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'salda.partite',
            'view_id': False,
            'context': context,
            'target':'new',
            'type': 'ir.actions.act_window',}
        
salda_partite()

class salda_partite_righe(osv.osv_memory):
    _name = 'salda.partite.righe'
    _description = 'Wizard di Salda Partite righe'
    _columns = {
                    'testa_saldaconto': fields.many2one('salda.partite', 'Testata Wizard Saldaconto',ondelete='cascade', required=True, select=True),
                    'scadenza_id':fields.many2one('account.partite_scadenze', 'Scadenza',ondelete='cascade',readonly=True, required=True, select=True),                         
                    'data_scadenza':fields.date('Data Scadenza', required=True, readonly=True, select=True),
                    'importo': fields.float('Importo', digits_compute=dp.get_precision('Account'),readonly=True, help="Importo Scadenza"),
                    'da_saldare': fields.float('Da Saldare', digits_compute=dp.get_precision('Account'),readonly=True, help="Importo da Incassare o Pagare"),
                    'saldatt': fields.float('Attuale', digits_compute=dp.get_precision('Account'),readonly=False, help="Importo Attuale"),
                    'flg_salda':fields.boolean('Salda Riga', required=False),
                    'flg_salda_abb':fields.boolean('Salda Abbuono', required=False),
                    'abbuono': fields.float('Abbuono', digits_compute=dp.get_precision('Account'),readonly=True, help="Importo Attuale"),
                    #'tipo_documento': fields.related('causale_id', 'tipo_documento', string='Tipo Documento', type='char', relation='causcont',states={'posted':[('readonly',True)]}),
                    'numero_doc':fields.char('Numero Doc.',size=30,readonly=True),
                    'data_doc':fields.date('Data Doc.', required=False, readonly=True,), 
                    'protocollo':fields.integer('Protocollo', readonly=True),
                    'tipo_documento':fields.selection([("FA", "Fattura"),
                                                ('FC', 'Fattura Corrispettivi'),
                                                ('CO', 'Corrispettivi Scorporo'),
                                                ('NC', 'Nota Credito'),
                                                ('FCEE', 'Fatt. CEE'),
                                                ('NCEE', 'NC CEE'),
                                                ('ZZ', 'No Documento')],"Tipo Documento"),    

                }
    _order = 'data_scadenza,data_doc'
    
    def onchange_flg_salda_abb(self,cr,uid,ids,flg_salda_abb,da_saldare,saldatt,scadenza_id,partner_id,abbuono,context=None):
        res={}
        domain={}
        warning={}        
        
        if ids: 
            riga = self.browse(cr,uid,ids)[0]
            id_testa = [riga.name.id]
            testa = self.pool.get('salda.partite').browse(cr,uid,id_testa,context)[0]
            importo_resi= testa.importo_resi
        else:
            id_testa = False 

        if flg_salda_abb:
                # riporta un abbuono
                if saldatt<>0:
                   abbuono = da_saldare
                   da_saldare = 0.0
        else:
                    da_saldare += abbuono
                    abbuono = 0.0
        res['da_saldare']= da_saldare
        res['abbuono']= abbuono
        ok = self.write(cr,uid,ids,{'da_saldare':res['da_saldare'],'abbuono':res['abbuono'],})
        return  {'value':res,'domain':domain,'warning':warning}
        
        
    def onchange_flg_salda(self,cr,uid,ids,flg_salda,importo_oper,importo_resi,da_saldare,saldatt,scadenza_id,partner_id,context=None):
      res ={}   
      if importo_oper<>0:
        #saldatt = 0
        domain={}
        warning={}        
        if not context:
            context={}       
        importo_resi=0
        #import pdb;pdb.set_trace()
        if ids: 
            riga = self.browse(cr,uid,ids)[0]
            id_testa = [riga.testa_saldaconto.id]
            testa = self.pool.get('salda.partite').browse(cr,uid,id_testa,context)[0]
            importo_resi= testa.importo_resi
        else:
            id_testa = False 
        if scadenza_id:
            #import pdb;pdb.set_trace()
            scad_obj = self.pool.get('account.partite_scadenze').browse(cr,uid,scadenza_id,context)
            # prima devo controllare lo stato di flag.
            if flg_salda:
                # è passato da falso a true  quindi deve saldare la partita
              if importo_resi<>0:
                # calcolo 'l'attuale della scadenza
                result = self.calcola_residuo(cr, uid,ids, importo_resi, importo_oper, da_saldare, saldatt, flg_salda, scadenza_id, context)
                res['importo_resi']= result.get('importo_resi',0.0)
                res['da_saldare']=result.get('da_saldare',0.0)
                res['saldatt']= result.get('saldatt',0.0)
              else:
                 # non c'è + nulla da saldare deve 
                 flg_salda = False    
            else: # non vuole + saldare la partita
                #import pdb;pdb.set_trace()
                importo_resi += saldatt
                res['da_saldare']=da_saldare+saldatt               
                res['importo_resi']= importo_resi
                res['saldatt']= 0.0
                saldatt = 0
            #import pdb;pdb.set_trace()
            ok = self.write(cr,uid,ids,{'da_saldare':res['da_saldare'],'saldatt':res['saldatt']})
            if id_testa:
                #importo_residuo = res.get('importo_resi',0.0)
                #ok = self.pool.get('salda.partite').write(cr,uid, [id_testa],{'importo_resi':importo_residuo})
                ok = self.pool.get('salda.partite').check(cr, uid, id_testa, context)
            
            
        return  {'value':res,'domain':domain,'warning':warning}    
    
 # VANNO ANCORA GESTITI GLI EVENTUALI ABBUONI ATTIVI O PASSIVI   
    def calcola_residuo(self,cr,uid,ids,importo_resi,importo_oper,da_saldare,saldatt,flg_salda,scadenza_id,context=None):
        res = {}
        if not context:
            context={}        
        if scadenza_id:
            #import pdb;pdb.set_trace()
            scad_obj = self.pool.get('account.partite_scadenze').browse(cr,uid,scadenza_id,context)
            causale_pnt = scad_obj.name.reg_pnt.causale_id
            calcolato = False
            if ids:
                        riga = self.browse(cr,uid,ids)[0]
                        id_testa = [riga.testa_saldaconto.id]
                        testa = self.pool.get('salda.partite').browse(cr,uid,id_testa,context)[0]
                        causale_testa = testa.causale_id
            if causale_testa.flag_cliente == causale_pnt.flag_cliente and causale_testa.flag_fornitore == causale_pnt.flag_fornitore:
                # si tratta di una riga normale di incasso e pagamento
                flag_compensa = False
            else:
                # deve fare una compensazione per questa riga, deve cioè mettere in prima nota l'importo di questa riga non con il conto di incasso o pagamento 
                # ma con il conto mastro cliente fornitore presente sulla riga di apertura della scadenza stessa, il totale importo operazione viene poi aumentato/decrementato di questo importo
                flag_compensa = True 
            if not causale_pnt.tipo_documento or causale_pnt.tipo_documento=="ZZ" :
                # SE SULLA RIGA DELLA REGISTRAZIONE CHE HA GENERATO LA PARTITA IL SEGNO È UGUALE A QUELLO DELLA CAUSALE DI 
                # INCASSO O PAGAMENTO, SOMMA COME SE FOSSE NC SE È DIVERSO DEVE DETRARRE
                riga_pnt = scad_obj.name.riga_reg_pnt
                if riga_pnt.credit <> 0 : segno = "DA"
                if riga_pnt.debit <> 0 : segno = "AV"
                if ids:
                        riga = self.browse(cr,uid,ids)[0]
                        id_testa = [riga.testa_saldaconto.id]
                        testa = self.pool.get('salda.partite').browse(cr,uid,id_testa,context)[0]
                        if testa.segno_riga == segno and flg_salda:
                            attuale = da_saldare
                            importo_resi += da_saldare
                            da_saldare = 0
                            calcolato = True
                        if testa.segno_riga == segno and not flg_salda:   
                            importo_resi -= saldatt
                            attuale = 0
                            calcolato = True
                        if testa.segno_riga != segno and flg_salda:  
                            # è una fattura e vuole  saldarla quindi aggiorna attuale e diminuisce l'importo in residuo
                            if importo_resi> da_saldare: 
                                attuale = da_saldare
                                importo_resi -= attuale                    
                                calcolato = True
                                da_saldare = 0
                            else:
                                attuale = importo_resi
                                importo_resi -= attuale                   
                                calcolato = True
                                da_saldare -= attuale
                        if testa.segno_riga != segno and not flg_salda:      
                            # è una fattura e non vuole + saldarla quindi inverte il segno del calcolo
                            importo_resi += attuale
                            da_saldare +=attuale
                            attuale = 0                                      
                            calcolato = True
                                                                              
            if 'NC' in causale_pnt.tipo_documento and flg_salda:
                # è una nota credito quindi e deve saldarla quindi  aggiorna attuale e somma l'importo in residuo
                attuale = da_saldare
                importo_resi += da_saldare
                da_saldare = 0
                calcolato = True
            if 'NC' in causale_pnt.tipo_documento and not flg_salda:
                # è una nota credito quindima non vuole + saldarla quindi il aggiorna attuale e somma l'importo in residuo
                importo_resi -= saldatt
                attuale = 0
                calcolato = True
            if 'F' in causale_pnt.tipo_documento and flg_salda:
                # è una fattura e vuole  saldarla quindi aggiorna attuale e diminuisce l'importo in residuo
                if importo_resi> da_saldare: 
                    attuale = da_saldare
                    importo_resi -= attuale                    
                    calcolato = True
                    da_saldare = 0
                else:
                    attuale = importo_resi
                    importo_resi -= attuale                   
                    calcolato = True
                    da_saldare -= attuale
            if 'F' in causale_pnt.tipo_documento and not flg_salda:
                # è una fattura e non vuole + saldarla quindi inverte il segno del calcolo
                    importo_resi += attuale
                    da_saldare +=attuale
                    attuale = 0                                      
                    calcolato = True
        return {'saldatt':attuale,'da_saldare':da_saldare,'importo_resi':importo_resi}
    
    
    
salda_partite_righe()