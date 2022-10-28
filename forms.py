from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import Form as NoCsrfForm
from wtforms import FieldList, FormField, StringField, TextField, SubmitField, IntegerField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, IPAddress, Regexp, NumberRange, ValidationError
import re
import ipaddress

class IpToMaskMatch(object):
    """
    Compares the values of two fields.
    :param maskfieldname:
        The name of the field containing subnet mask.
    :param message:
        Error message to raise in case of a validation error. Can be
        interpolated with `%(maskfield_label)s` and `%(maskfield_name)s` to provide a
        more helpful error.
    """
    def __init__(self, maskfieldname, message=None):
        self.maskfieldname = maskfieldname
        self.message = message

    def __call__(self, form, field):
        try:
            maskfield = form[self.maskfieldname]
        except KeyError:
            raise ValidationError(field.gettext("Invalid field name '%s'.") % self.maskfieldname)

        try: 
            net = ipaddress.ip_network(str(field.data) + '/' + str(maskfield.data))
        except ValueError:
            d = {
                'maskfield_label': hasattr(maskfield, 'label') and maskfield.label.text or self.maskfieldname,
                'maskfield_name': self.maskfieldname
            }
            if self.message is None:
                self.message = field.gettext('IP does not match mask in %(maskfield_label)s.')
            raise ValidationError(self.message % d)

class MaskToIpMatch(object):
    """
    Compares the values of two fields.
    :param ipfieldname:
        The name of the field containing ip address.
    :param message:
        Error message to raise in case of a validation error. Can be
        interpolated with `%(ipfield_label)s` and `%(ipdfield_name)s` to provide a
        more helpful error.
    """
    def __init__(self, ipfieldname, message=None):
        self.ipfieldname = ipfieldname
        self.message = message

    def __call__(self, form, field):
        try:
            ipfield = form[self.ipfieldname]
        except KeyError:
            raise ValidationError(field.gettext("Invalid field name '%s'.") % self.ipfieldname)

        try: 
            net = ipaddress.ip_network(str(ipfield.data) + '/' + str(field.data))
        except ValueError:
            d = {
                'ipfield_label': hasattr(ipfield, 'label') and ipfield.label.text or self.ipfieldname,
                'ipfield_name': self.ipfieldname
            }
            if self.message is None:
                self.message = field.gettext('Mask does not match IP in %(ipfield_label)s.')
            raise ValidationError(self.message % d)


class siteItem(NoCsrfForm):
    code = StringField('Site code', render_kw={"placeholder": "SITECODE01"}, 
        validators=[
            Length(min=10, max=15, message='Site ID should have 10-15 characters.'),
            DataRequired()
        ])
    alias = StringField('Site alias', render_kw={"placeholder": "site01"}, 
        validators=[
            DataRequired()
        ])
    location = StringField('Location', render_kw={"placeholder": "HOUSTON, TEXAS, USA"}, 
        validators=[
            Regexp('^[A-Z]+, [A-Z]+, (CANADA|USA)$', flags=re.IGNORECASE, message= 'Please enter location in format CITY, STATE, COUNTRY (CANADA/USA only).'), 
            DataRequired()
        ])
    primary_wan_type = SelectField('Type', choices=[
            ('mpls', 'MPLS Provider 1'),
            ('isp1', 'Internet Provider 1'),
            ('isp2', 'Internet Provider 2')
        ], validators=[
            DataRequired()
        ])
    secondary_wan_type = SelectField('Type', choices=[
            ('isp1', 'Internet Provider 1'),
            ('mpls', 'MPLS Provider 1'),
            ('isp2', 'Internet Provider 2')
        ], validators=[
        DataRequired()
        ])
    critical = SelectField('Critical site', choices=[
            ('no', 'No'),
            ('yes', 'Yes')
        ], validators=[
            DataRequired()
        ])

class wanItem(NoCsrfForm):
    logical_handoff = SelectField('Logical handoff', choices=[
            ('p2p', 'Point-to-Point'),
            ('vlan', 'VLAN')
        ], validators=[
            DataRequired()
        ])
    transit_vlan = IntegerField('Transit VLAN ID', render_kw={"placeholder": "241"}, 
        validators=[
            Optional(),
            NumberRange(min=1, max=4094, message='Please enter valid VLAN ID in range 1 - 4094.')
        ])
    physical_handoff = SelectField('Physical handoff', choices=[
            ('mmf', 'Multi-Mode Fiber'),
            ('smf', 'Single-Mode Fiber'),
            ('copper', 'Copper')
        ], validators=[
            DataRequired()
        ])
    access_id = StringField('Access ID', render_kw={"placeholder": "ACC12345"}, 
        validators=[
            DataRequired()
        ])
    port_id = StringField('Port ID', render_kw={"placeholder": "PRT12345"}, 
        validators=[
            DataRequired()
        ])
    speed = StringField('Port speed (kbps)', render_kw={"placeholder": "10000"}, 
        validators=[
            Regexp(r'^[1-9][0-9]*000$', message= 'Please enter WAN port speed in kbps e.g. 5000, 10000, 20000, etc.'), 
            DataRequired()
        ])
    net = StringField('WAN transit subnet', render_kw={"placeholder": "10.10.10.0"}, 
        validators=[
            IPAddress(message='Please enter a valid IP address.'), 
            IpToMaskMatch('mask'),
            DataRequired()
        ])
    mask = IntegerField('WAN transit mask', render_kw={"placeholder": "30"}, 
        validators=[
            NumberRange(min=24, max=30, message='Please enter agreed transit subnet mask in range 24-30.'),
            MaskToIpMatch('net')
        ])
    pe_as = IntegerField('WAN provider BGP ASN', render_kw={"placeholder": "65512"}, 
        validators=[
            NumberRange(min=1, max=65535, message='Please enter valid BGP ID of the PE router in range 1-65535.')
        ])   
    router = SelectField('Router model', choices=[
            ('isr4331', 'ISR4331'),
            ('isr4431', 'ISR4431'),
            ('2921', '2921')
        ], validators=[
            DataRequired()
    ])
    router_num = StringField('Router CMDB #', render_kw={"placeholder": "01"}, 
        validators=[
            Regexp('[0-9][0-9]', message= 'Please enter CMDB router number, e.g. 01, 07, etc.'), 
            DataRequired()
        ])
    loopback_ip = StringField('Router loopback IP', render_kw={"placeholder": "10.1.1.1"}, 
        validators=[
            IPAddress(message='Please enter a valid IP address.'), 
            DataRequired()
        ])
    ce_as = IntegerField('Router BGP ASN', render_kw={"placeholder": "65513"}, 
        validators=[
            NumberRange(min=1, max=65535, message='Please enter valid BGP ID of the PE router in range 1-65535.')
            ])

class vlanItem(NoCsrfForm):
    vlan_id = IntegerField('VLAN ID', render_kw={"placeholder": "500"}, 
        validators=[
            NumberRange(min=1, max=4094, message='Please enter valid VLAN ID in range 1 - 4094.')
            ])
    vlan_name = StringField('VLAN name', 
        validators=[
            Length(min=3, max=31, message='VLAN name should have 3-31 characters.'),
            DataRequired()
        ])
    net = StringField('VLAN network address',
        validators=[
            IPAddress(message='Please enter a valid IP address.'), 
            IpToMaskMatch('mask'),
            DataRequired()
        ])
    mask = IntegerField('VLAN network mask', 
        validators=[
            NumberRange(min=16, max=30, message='Please enter valid vlan mask. Format is number in range 16-30.'),
            MaskToIpMatch('net')
        ])

class idfItem(NoCsrfForm):
    switch_count = SelectField('Switch port count', choices=[
            ('0', '0'),
            ('0.55', '24'),
            ('1', '48'),
            ('2', '96'),
            ('3', '144'),
            ('4', '192'),
            ('5', '240'),
            ('6', '288'),
            ('7', '336'),
            ('8', '386'),
            ('9', '432')
        ], validators=[
            DataRequired()
    ])

class lanportsItem(NoCsrfForm):
    printer = IntegerField('Printer', render_kw={"placeholder": "0"}, validators=[Optional()])
    camera = IntegerField('Camera', render_kw={"placeholder": "0"},  validators=[Optional()])
    server = IntegerField('Server', render_kw={"placeholder": "0"}, validators=[Optional()])

class rdsForm(FlaskForm):
    sr_num = StringField('Service Request number', render_kw={"placeholder": "1234567"}, 
        validators=[
            Length(min=7, max=15, message='Service Request number should have 7-15 characters.'),
            Regexp('[1-9][0-9]+', message= 'Service Request number should be a number that does not start with zero.'),
            DataRequired()
            ])
    userid = StringField("Your userid", render_kw={"placeholder": "user01"},
    validators=[
            Length(min=6, max=6, message='Your userid should have 6 alphanumeric characters.'),
            Regexp(r'\w+', message= 'userid should contain only alphanumeric characters '),
            DataRequired()
        ])
    business_unit = SelectField('Business Unit', choices=[
        ('bu1', 'Business Unit 1'),
        ('bu2', 'Business Unit 2'),
        ('bu3', 'Business Unit 3'),
        ('bu4', 'Business Unit 4')
    ], validators=[
        DataRequired()
    ])
    site = FormField(siteItem, label='Site')
    wan = FieldList(FormField(wanItem), label='WANs', min_entries=1, max_entries=2, validators=[DataRequired()])
    vlan = FieldList(FormField(vlanItem), label='Vlans', min_entries=3, validators=[DataRequired()])
    idf = FieldList(FormField(idfItem), label='IDFs', min_entries=1, validators=[DataRequired()])
    lanports = FormField(lanportsItem, label='LAN ports reservation')
    note = TextAreaField(label='Note', render_kw={"placeholder": "max. 200 characters"}, validators=[Optional(), Length(max=200)])
    submit = SubmitField('Create Dataset File')

class leForm(FlaskForm):
    rds_file = FileField(label='Please upload the Dataset file in YAML format')
    submit = SubmitField('Generate Staging Files')

class diagramForm(FlaskForm):
    inventory_file = FileField(label='Please upload the inventory file in YAML format')
    submit = SubmitField('Render Network Diagram')