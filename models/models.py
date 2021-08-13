from odoo import models, fields, api, _
from odoo.exceptions import UserError

class res_partner(models.Model):
    _inherit = "res.partner"

    identitas = fields.Char(string='NIK')
    nama_ayah = fields.Char(string='Nama Ayah')
    nama_ibu = fields.Char(string='Nama Ibu')
    tmp_lahir = fields.Char(string='Tempat Lahir')
    tgl_lahir = fields.Date(string='Tanggal Lahir')
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
        string='Tanggal',
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

