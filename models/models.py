import base64
import xlsxwriter

from typing import BinaryIO, ChainMap
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class res_partner(models.Model):
    _inherit = "res.partner"

    identitas = fields.Char(string='NIK')
    nama_ayah = fields.Char(string='Nama Ayah')
    nama_ibu = fields.Char(string='Nama Ibu')
    tmp_lahir = fields.Char(string='Tempat Lahir')
    tgl_lahir = fields.Date(string='Tanggal Lahir')
    umur = fields.Integer(
        string='Umur',
        compute="_coumpute_umur",
        readonly=True, states={"draft": [("readonly", False)]}
    )
    gol_darah = fields.Selection([
        ('a','A'),
        ('b','B'),
        ('ab','AB'),
        ('o','O')], string='Golongan Darah')
    jk = fields.Selection([
        ('pria','Laki-Laki'),
        ('wanita','Perempuan'),], string='Jenis Kelamin')
    status_pk = fields.Selection([
        ('belum','Single'),
        ('menikah','Married'),
        ('cerai','Divorce'),], string='Status Perkawinan')
    pendidikan = fields.Selection([
        ('sd','SD'),
        ('smp','SMP'),
        ('sma','SMA'),
        ('s1','S1')
        ('s2','S2')
        ('s3','S3')], string='Pendidikan')
    
    @api.depends('tgl_lahir')
    def _compute_umur(self):
        for i in self:
            i.umur = False
            today = fields.Date.today()
            if i.tgl_lahir:
                delta = today - i.tgl_lahir
                i.umur = int(delta.days/365)
            else:
                i.umur = 0

class paket_perjalanan(models.Model):
    _name = 'paket.perjalanan'

    name = fields.Char(
        string='Reference', 
        readonly=True, 
        default='/')
    product_id = fields.Many2one(
        comodel_name='product.product',
        string="Product",
        required=True,
        # related="product.product",
        readonly=True, states={"draft": [("readonly", False)]}
    )
    tgl_berangkat = fields.Date(
        string='Tanggal Berangkat',
        required=True,
        readonly=True, states={"draft": [("readonly", False)]}
    )
    tgl_pulang = fields.Date(
        string='Tanggal Pulang',
        required=True,
        readonly=True, states={"draft": [("readonly", False)]}
    )
    kuota = fields.Integer(
        string="Kuota",
        readonly=True, states={"draft": [("readonly", False)]}
    )
    kuota_progress = fields.Float(
        string='Kuota Terisi',
        compute='_taken_seats'    
    )
    note = fields.Text(
        string='Notes',
        readonly=True, states={"draft": [("readonly", False)]}
    )
    hotel_list = fields.One2many(
        comodel_name="paket.hotel.line",
        inverse_name="paket_perjalanan_id",
        string="List Hotel",
        readonly=True, states={"draft": [("readonly", False)]}
    )
    pesawat_list= fields.One2many(
        comodel_name="paket.pesawat.line",
        inverse_name="paket_perjalanan_id",
        string="List Penerbangan",
        readonly=True, states={"draft": [("readonly", False)]}
    )
    acara_list = fields.One2many(
        comodel_name="paket.acara.line",
        inverse_name="paket_perjalanan_id",
        string='List Jadwal',
        readonly=True, states={"draft": [("readonly", False)]}
    )
    peserta_list = fields.One2many(
        comodel_name="paket.peserta.line",
        inverse_name="paket_perjalanan_id",
        string='List Jamaah',
        readonly=True
    )
    state = fields.Selection([
        ('draft','Draft'),
        ('confirm','Confirmed')], 
        string='Status',
        readonly=True, 
        copy=False, 
        default='draft',
        track_visibility='onchange'
    )
    filename = fields.Char(
        string='Filename',
        readonly=True, states={"draft": [("readonly", False)]}
    )
    data_file = fields.Binary(
        string='Data file',
        readonly=True, states={"draft": [("readonly", False)]}
    )

    def action_confirm(self):
        self.write({'state': 'confirm'})
    
    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('paket.perjalanan')
        return super(paket_perjalanan, self).create(vals)

    def name_get(self):
        return [(this.id, this.name + "#" + " " + this.product_id.partner_ref) for this in self]
    
    @api.depends('kuota', 'peserta_list')
    def _taken_seats(self):
        for r in self:
            if not r.kuota:
                r.kuota_progress = 0.0
            else:
                r.kuota_progress = 100.0 * len(r.peserta_list) / r.kuota

    def update_jamaah(self):
        order_ids = self.env['sale.order'].search([('paket_perjalanan_id', '=', self.id), ('state', 'not in', ('draft', 'cancel'))])
        if order_ids:
            self.peserta_list.unlink()
            for o in order_ids:
                for x in o.passport_line:
                    self.peserta_list.create({
                        'paket_perjalanan_id': self.id,
                        'partner_id': x.partner_id.id,
                        'name': x.name,
                        'order_id': o.id,
                        'jenis_kelamin': x.partner_id.jk,
                        'tipe_kamar': x.tipe_kamar,
                    })
    
    def cetak_jamaah_xls(self):
        last_row = 4
        count = 0

        # Membuat Worksheet
        folder_title = self.name + "-" + str(date.today()) + ".xlsx"
        file_data = BytesIO()
        workbook = xlsxwriter.Workbook(file_data)
        sheet = workbook.add_worksheet((self.name))

        # Menambahkan style
        style = workbook.add_format({'left': 1, 'top': 1,'right':1,'bold': True,'fg_color': '#0000ff','font_color': 'white','align':'center'})
        style.set_text_wrap()
        style.set_align('vcenter')
        style_bold = workbook.add_format({'left': 1, 'top': 1,'right':1,'bottom':1,'bold': True,'align':'center'})
        style_bold_orange = workbook.add_format({'left': 1, 'top': 1,'right':1,'bold': True,'align':'center','fg_color': '#00b5ff','font_color': 'white'})
        style_no_bold = workbook.add_format({'left': 1,'right':1,'bottom':1})
        style_date = workbook.add_format({'left': 1,'right':1,'bottom':1, 'num_format':'dd/mm/yyyy'})
        
        sheet.set_column(1, 1, 10)
        sheet.set_column(1, 12, 25)

        sheet.write(1, 1, 'Data Lengkap', style_no_bold)
        sheet.write(1, 2, self.name, style_no_bold)

        # Mencetak header
        sheet.write(3, 0,'No', style_bold_orange)
        sheet.write(3, 1,'Title', style_bold_orange)
        sheet.write(3, 2, 'Jenis Kelamin', style_bold_orange)
        sheet.write(3, 3, 'Nama Lengkap', style_bold_orange)
        sheet.write(3, 4, 'Tempat Lahir', style_bold_orange)
        sheet.write(3, 5, 'Tanggal Lahir', style_bold_orange)
        sheet.write(3, 6, 'ID Passport', style_bold_orange)
        sheet.write(3, 7, 'Passport Issue', style_bold_orange)
        sheet.write(3, 8, 'Masa Berlaku Passport', style_bold_orange)
        sheet.write(3, 9, 'Imigrasi Asal', style_bold_orange)
        sheet.write(3, 10, 'Mahram', style_bold_orange)
        sheet.write(3, 11, 'Umur', style_bold_orange)
        sheet.write(3, 12, 'NIK', style_bold_orange)
       
        # looping for table body
        for line in self.peserta_list:
            passport = self.env['sale.passport.line'].search([('partner_id', '=', line.partner_id.id)])

            sheet.write(last_row, 0, str(count+1), style_no_bold)
            if line.partner_id.title.name:
                sheet.write(last_row, 1, line.partner_id.title.name, style_no_bold)
            else:
                sheet.write(last_row, 1, 'None', style_no_bold)

            sheet.write(last_row, 2, line.partner_id.jk, style_no_bold)
            sheet.write(last_row, 3, line.partner_id.name, style_no_bold)
            sheet.write(last_row, 4, line.partner_id.tmp_lahir, style_date)
            sheet.write(last_row, 5, line.partner_id.tgl_lahir, style_date)
            sheet.write(last_row, 6, passport.nomor, style_no_bold)
            sheet.write(last_row, 7, passport.order_id.date_order, style_date)
            sheet.write(last_row, 8, passport.masa_berlaku, style_date)
            sheet.write(last_row, 9, line.partner_id.city, style_no_bold)
            sheet.write(last_row, 10, line.partner_id.mahram.name, style_no_bold)
            sheet.write(last_row, 11, line.partner_id.umur, style_no_bold)
            sheet.write(last_row, 12, line.partner_id.nidentitas, style_no_bold)

            last_row += 1
            count += 1

        count = 0
        last_row +=2

        sheet.write(last_row, 2,'No', style_bold_orange)
        sheet.write(last_row, 3,'Maskapai', style_bold_orange)
        sheet.write(last_row, 4, 'Tanggal keberangkatan', style_bold_orange)
        sheet.write(last_row, 5, 'Kota Asal', style_bold_orange)
        sheet.write(last_row, 6, 'Kota Asal', style_bold_orange)

        last_row += 1

        for line in self.pesawat_list:
            sheet.write(last_row, 2, str(count), style_no_bold)
            sheet.write(last_row, 3, line.partner_id.name, style_no_bold)
            sheet.write(last_row, 4, line.tgl_berangkat, style_no_bold)
            sheet.write(last_row, 5, line.kota_asal, style_no_bold)
            sheet.write(last_row, 6, line.kota_tujuan, style_no_bold)

            last_row += 1
            count += 1
            
        # Menyimpan data di field data_file
        workbook.close()        
        out = base64.encodestring(file_data.getvalue())
        self.write({'data_file': out, 'filename': folder_title})

        return self.view_form()

    def view_form(self):        
        # view = self.env.ref('nr_travel_umroh.report_excel_wizard')
        return {
            'name': _('Product Report Wizard'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'paket.perjalanan',
            'viesheet': [(view.id, 'form')],
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

class paket_hotel_line(models.Model):
    _name = "paket.hotel.line"
    
    paket_perjalanan_id = fields.Many2one(
        comodel_name='paket.perjalanan', 
        string='Paket Perjalanan', 
        ondelete='cascade'
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner', 
        string='Hotel', 
        required=True
    )
    tgl_awal = fields.Date(
        string='Tanggal Mulai', 
        required=True
    )
    tgl_akhir = fields.Date(
        string='Tanggal Berakhir', 
        required=True
    )
    kota = fields.Char(
        related='partner_id.city', 
        string='Kota', 
        readonly=True
    )
 
class paket_pesawat_line(models.Model):
    _name = "paket.pesawat.line"
    
    paket_perjalanan_id = fields.Many2one(
        comodel_name='paket.perjalanan',
        string='Paket Perjalanan',
        ondelete='cascade'
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Maskapai Penerbangan',
        required=True
    )
    tgl_berangkat = fields.Date(
        string='Tanggal keberangkatan', 
        required=True
    )
    kota_asal = fields.Char(
        string='Kota Asal',
        required=True
    )
    kota_tujuan = fields.Char(
        string='Kota Tujuan',
        required=True
    )
 
class paket_acara_line(models.Model):
    _name = "paket.acara.line"
    
    paket_perjalanan_id = fields.Many2one(
        comodel_name='paket.perjalanan',
        string='Paket Perjalanan',
        ondelete='cascade'
    )
    name = fields.Char(
        string='Nama',
        required=True
    )
    tgl = fields.Date(
        string='Tanggal Acara',
        required=True
    )
 
class paket_peserta_line(models.Model):
    _name = "paket.peserta.line"
    
    paket_perjalanan_id = fields.Many2one(
        comodel_name='paket.perjalanan',
        string='Paket Perjalanan',
        ondelete='cascade'
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Jamaah'
    )
    name = fields.Char(
        string='Nama pada Passport',
        required=True
    )
    order_id = fields.Many2one(
        comodel_name='sale.order',
        string='Sales Orders',
        ondelete='cascade'
    )
    jk = fields.Selection([
        ('pria','Laki-Laki'),
        ('wanita','Perempuan'),], string='Jenis Kelamin')
    tipe_kamar = fields.Selection([
        ('d', 'Double'), 
        ('t', 'Triple'), 
        ('q', 'Quad')], 
        string='Room Type', 
        required=True
    )


class sale_order(models.Model):
    _inherit = "sale.order"

    paket_perjalanan_id = fields.Many2one(
        comodel_name='paket.perjalanan',
        string='Paket Perjalanan',
        domain=[('state', '=', 'confirm')]
    )
    dokumen_line = fields.One2many(
        comodel_name='sale.dokumen.line',
        inverse_name='order_id',
        string='List Dokumen'
    )
    passport_line = fields.One2many(
        comodel_name='sale.passport.line',
        inverse_name='order_id',
        string='List Passport'
    )

    @api.onchange('paket_perjalanan_id')
    def set_order_line(self):
        # res = {}
        if self.paket_perjalanan_id:
            order = self.env['sale.order'].new({
                'name' : self.name,
                'partner_id': self.partner_id.id,
                'partner_invoice_id' : self.partner_id.id,
                'partner_shipping_id' : self.partner_id.id,
                'pricelist_id': self.pricelist_id.id,
                'company_id' : self.company_id.id,
                'date_order': self.date_order
            })

            pp = self.paket_perjalanan_id
            new_order_line = self.env['sale.order.line'].new({
                'product_id': pp.product_id.id,
                'name' : '',
                'order_id' : order.id,
                'product_uom_qty': 1,
            })
            new_order_line.product_id_change()
            self.order_line = new_order_line

class sale_dokumen_line(models.Model):
    _name = "sale.dokumen.line"

    order_id = fields.Many2one(
        comodel_name='sale.order',
        string='Sales Orders',
        ondelete='cascade'
    )
    name = fields.Char(
        string='Nama',
        required=True
    )
    foto = fields.Binary(
        string='Photo', 
        required=True
    )


class sale_passport_line(models.Model):
    _name = "sale.passport.line"

    order_id = fields.Many2one(
        comodel_name='sale.order',
        string='Sales Orders',
        ondelete='cascade'
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Jamaah',
        required=True
    )
    nomor = fields.Char(
        string='ID Passport',
        required=True
    )
    name = fields.Char(
        string='Nama pada Passport',
        required=True
    )
    masa_berlaku = fields.Date(
        string='Berlaku Sampai Dengan',
        required=True
    )
    tipe_kamar = fields.Selection([
        ('d', 'Double'), 
        ('t', 'Triple'), 
        ('q', 'Quad')], 
        string='Room Type', 
        required=True
    )
    foto = fields.Binary(
        string='Photo', 
        required=True
    )