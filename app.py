from flask import Flask, render_template, redirect, url_for, current_app, send_from_directory
from forms import rdsForm, leForm, diagramForm
import datetime
import os
import ipaddress
import yaml

app = Flask(__name__)

secret_key = os.urandom(32)
app.config['SECRET_KEY'] = secret_key

@app.template_filter()
def ip_and_mask(ip, mask, num, delim):
    net = ipaddress.ip_network(str(ip) + '/' + str(mask))
    return str(net[num]) + delim + str(net.netmask)

@app.template_filter()
def ip_increment(ip, inc):
    ip = ipaddress.ip_address(ip)
    return ip + inc

@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template("index.html")

@app.route('/about', methods=['GET', 'POST'])
def about():
    return render_template("about.html")

@app.route('/customer1/rds-form', methods=['GET', 'POST'])
def rds_form_customer1():
    form = rdsForm()
    if form.validate_on_submit():
        
        folder_path = os.path.join(current_app.root_path, 'staging', 'customer1', str(form.sr_num.data))
        os.makedirs(folder_path, exist_ok=True)
        file_path = os.path.join(folder_path, "{}_data.yml".format(str(form.sr_num.data)))
        with open(file_path, 'w', newline="\r\n") as generated_file:
            yaml.dump(form.data, generated_file)

        return send_from_directory(directory=folder_path, filename="{}_data.yml".format(str(form.sr_num.data)), as_attachment=True)
    return render_template('rds-form-customer1.html', form=form)

@app.route('/le/customer1/rds-upload', methods=['GET', 'POST'])
def rds_upload_customer1():
    form = leForm()
    
    if form.validate_on_submit():
        rds = yaml.load(form.rds_file.data)
        folder_path = os.path.join(current_app.root_path, 'staging', 'customer1', str(rds['sr_num']))
        os.makedirs(folder_path, exist_ok=True)
        file_path = os.path.join(folder_path, "{}_data.yml".format(str(rds['sr_num'])))
        with open(file_path, 'w', newline="\r\n") as generated_file:
            yaml.dump(rds, generated_file)

        # START: determine device naming convention
        if 'usa' in rds['site']['location'].lower():
            device_naming = 'us-{}-'.format(rds['site']['alias'].lower())
        elif 'canada' in rds['site']['location'].lower():
            device_naming = 'ca-{}-'.format(rds['site']['alias'].lower())
        else:
            device_naming = 'country_code-{}-'.format(rds['site']['alias'].lower())
        # end: determine device naming convention

        # inventory variable will be filled out during the workflow
        inventory = {
            'sr_num': rds['sr_num'],
            'userid': rds['userid'],
            'business_unit': rds['business_unit'],
            'primary_wan_type': rds['site']['primary_wan_type'],
            'secondary_wan_type': rds['site']['secondary_wan_type'],
            'site': {
                'alias': rds['site']['alias'],
                'code': rds['site']['code'],
                'location': rds['site']['location']
            },
            'wan': [{
                'name': 'Internet',
                'speed': None,
                'access_id': None,
                'port_id': None
            },{
                'name': 'Internet',
                'speed': None,
                'access_id': None,
                'port_id': None
            }],
            'routers': [{
                'asset_id': None,
                'name': rds['site']['primary_wan_type'].upper(),
                'model': None,
                'hw_count': 1,
                'mgmt_interface': None,
                'mgmt_ip': None,
                'uplinks': [],
                'downlinks': []
            },{
                'asset_id': None,
                'name': rds['site']['secondary_wan_type'].upper(),
                'model': None,
                'hw_count': 1,
                'mgmt_interface': None,
                'mgmt_ip': None,
                'uplinks': [],
                'downlinks': []
            }],
            'distro_switch': {
                'location': 'MDF',
                'asset_id': rds['site']['code'] + '_S01-1',
                'name': device_naming + 'sw01',
                'model': None,
                'port_count': None,
                'hw_count': None,
                'mgmt_interface': 'Vlan' + str(rds['vlan'][1]['vlan_id']),
                'mgmt_ip': str(ipaddress.ip_address(rds['vlan'][1]['net'])+5),
                'uplinks': [],
                'downlinks': []
            },
            'access_switches': [],
            'connections': [
              ['r1', 'WAN', 'wan_cloud1', 'LAN', 'copper'],
              ['r2', 'WAN', 'wan_cloud2', 'LAN', 'copper'],
              ['s1', 'uplink1', 'r1', 'LAN', 'copper'],
              ['s1', 'uplink2', 'r2', 'LAN', 'copper']
            ],
            'port_reservation': [],
            'port_reservation_text': r'Ports\n'
        }
    # START: WAN STAGING CONFIGS GENERATION --------------------------------------------------------------------------------

        # START: PRIMARY WAN -----------------------------------------------------------------------------------------------
        if rds['site']['primary_wan_type'] == 'mpls':

            inventory['wan'][0]['name'] = 'MPLS'
            inventory['wan'][0]['speed'] = int(int(rds['wan'][0]['speed'])/1000)
            inventory['wan'][0]['access_id'] = rds['wan'][0]['access_id']
            inventory['wan'][0]['port_id'] = rds['wan'][0]['port_id']
            inventory['connections'][0][4] = rds['wan'][0]['physical_handoff']
            inventory['routers'][0]['asset_id'] = rds['site']['code'] + '_' + rds['wan'][0]['router_num']
            inventory['routers'][0]['name'] = device_naming + 'rt01'
            inventory['routers'][0]['model'] = 'CISCO ' + rds['wan'][0]['router'].upper()
            inventory['routers'][0]['mgmt_interface'] = 'Lo0'
            inventory['routers'][0]['mgmt_ip'] = rds['wan'][0]['loopback_ip']

            if rds['wan'][0]['router'].startswith('isr4') and rds['wan'][0]['physical_handoff'] in ['smf', 'mmf']:
                inventory['routers'][0]['uplinks'].append('Gi0/0/2')
                inventory['routers'][0]['downlinks'].append('Gi0/0/0')
                inventory['connections'][0][1] = 'Gi0/0/2'
                inventory['connections'][2][3] = 'Gi0/0/0'
            elif rds['wan'][0]['router'].startswith('isr4') and rds['wan'][0]['physical_handoff'] == 'copper':
                inventory['routers'][0]['uplinks'].append('Gi0/0/1')
                inventory['routers'][0]['downlinks'].append('Gi0/0/0')
                inventory['connections'][0][1] = 'Gi0/0/1'
                inventory['connections'][2][3] = 'Gi0/0/0'
            elif rds['wan'][0]['router'] == '2921' and rds['wan'][0]['physical_handoff'] in ['smf', 'mmf']:
                inventory['routers'][0]['uplinks'].append('Gi0/1')
                inventory['routers'][0]['downlinks'].append('Gi0/0')
                inventory['connections'][0][1] = 'Gi0/1'
                inventory['connections'][2][3] = 'Gi0/0'
            elif rds['wan'][0]['router'] == '2921' and rds['wan'][0]['physical_handoff'] == 'copper':
                inventory['routers'][0]['uplinks'].append('Gi0/2')
                inventory['routers'][0]['downlinks'].append('Gi0/0')
                inventory['connections'][0][1] = 'Gi0/2'
                inventory['connections'][2][3] = 'Gi0/0'

            if rds['business_unit'] == 'bu1':
                if rds['wan'][0]['router'].startswith('isr4'):
                    rendered_content = render_template('configs/customer1/bu1_isr4k_r01.j2', rds=rds, date=datetime.date.today())
                else:
                    print('wrong BU/router combination')
                    ### redirect to error page should happen here instead of above print
                    
            elif rds['business_unit'] in ['bu2', 'bu3', 'bu4']:
                if rds['wan'][0]['router'].startswith('isr4'):
                    rendered_content = render_template('configs/customer1/bu2-4_isr4k_r01.j2', rds=rds, date=datetime.date.today())
                elif rds['wan'][0]['router'] == '2921':
                    rendered_content = render_template('configs/customer1/bu2-4_2921_r01.j2', rds=rds, date=datetime.date.today())
                else:
                    print('wrong BU/router combination')
                    ### redirect to error page should happen here instead of above print
            else:
                print('non-existent BU')
                ### redirect to error page should happen here instead of above print
            file_path = os.path.join(folder_path, "{}_R{}_staging.txt".format(str(rds['sr_num']), str(rds['wan'][0]['router_num'])))
            generated_file = open(file_path, 'w', newline="\r\n")
            generated_file.write(rendered_content)
            generated_file.close()
        else:
            inventory['routers'][0]['uplinks'].append('WAN')
            inventory['routers'][0]['downlinks'].append('LAN')
        # END: PRIMARY WAN -------------------------------------------------------------------------------------------------

        # START: SECONDARY WAN ---------------------------------------------------------------------------------------------
        if rds['site']['secondary_wan_type'] == 'mpls':

            inventory['wan'][1]['name'] = 'MPLS'
            inventory['wan'][1]['speed'] = int(int(rds['wan'][1]['speed'])/1000)
            inventory['wan'][1]['access_id'] = rds['wan'][1]['access_id']
            inventory['wan'][1]['port_id'] = rds['wan'][1]['port_id']
            inventory['connections'][1][4] = rds['wan'][1]['physical_handoff']
            inventory['routers'][1]['asset_id'] = rds['site']['code'] + '_' + rds['wan'][1]['router_num']
            inventory['routers'][1]['name'] = device_naming + 'r02'
            inventory['routers'][1]['model'] = 'CISCO ' + rds['wan'][1]['router'].upper()
            inventory['routers'][1]['mgmt_interface'] = 'Lo0'
            inventory['routers'][1]['mgmt_ip'] = rds['wan'][1]['loopback_ip']

            if rds['wan'][1]['router'].startswith('isr4') and rds['wan'][1]['physical_handoff'] in ['smf', 'mmf']:
                inventory['routers'][1]['uplinks'].append('Gi0/0/2')
                inventory['routers'][1]['downlinks'].append('Gi0/0/0')
                inventory['connections'][1][1] = 'Gi0/0/2'
                inventory['connections'][3][3] = 'Gi0/0/0'
            elif rds['wan'][1]['router'].startswith('isr4') and rds['wan'][1]['physical_handoff'] == 'copper':
                inventory['routers'][1]['uplinks'].append('Gi0/0/1')
                inventory['routers'][1]['downlinks'].append('Gi0/0/0')
                inventory['connections'][1][1] = 'Gi0/0/1'
                inventory['connections'][3][3] = 'Gi0/0/0'
            elif rds['wan'][1]['router'] == '2921' and rds['wan'][1]['physical_handoff'] in ['smf', 'mmf']:
                inventory['routers'][1]['uplinks'].append('Gi0/1')
                inventory['routers'][1]['downlinks'].append('Gi0/0')
                inventory['connections'][1][1] = 'Gi0/1'
                inventory['connections'][3][3] = 'Gi0/0'
            elif rds['wan'][1]['router'] == '2921' and rds['wan'][1]['physical_handoff'] == 'copper':
                inventory['routers'][1]['uplinks'].append('Gi0/2')
                inventory['routers'][1]['downlinks'].append('Gi0/0')
                inventory['connections'][1][1] = 'Gi0/2'
                inventory['connections'][3][3] = 'Gi0/0'

            if rds['business_unit'] == 'bu1':
                print('option of BU1 having backup MPLS is not defined')
                ### redirect to error page should happen here instead of above print
            elif rds['business_unit'] in ['bu2', 'bu3', 'bu4']:
                if rds['wan'][1]['router'].startswith('isr4'):
                    rendered_content = render_template('configs/customer1/bu2-4_isr4k_r02.j2', rds=rds, date=datetime.date.today())
                elif rds['wan'][1]['router'] == '2921':
                    rendered_content = render_template('configs/customer1/bu2-4_2921_r02.j2', rds=rds, date=datetime.date.today())
                else:
                    print('wrong BU/router combination')
                    ### redirect to error page should happen here instead of above print
            else:
                print('non-existent BU')
                ### redirect to error page should happen here instead of above print
            
            file_path = os.path.join(folder_path, "{}_R{}_staging.txt".format(str(rds['sr_num']), str(rds['wan'][1]['router_num'])))
            generated_file = open(file_path, 'w', newline="\r\n")
            generated_file.write(rendered_content)
            generated_file.close()
        else:
            inventory['routers'][1]['uplinks'].append('WAN')
            inventory['routers'][1]['downlinks'].append('LAN')
        # END: SECONDARY WAN -----------------------------------------------------------------------------------------------
    # END: WAN STAGING CONFIGS GENERATION ----------------------------------------------------------------------------------

    # START: LAN STAGING CONFIGS GENERATION --------------------------------------------------------------------------------
        # START: Port reservation for Printers, Cameras, Servers, etc. --------------------------------------------------------------
        port_reservation = [[] for member in range(max(round(float(rds['idf'][0]['switch_count'])), 2))]
        for item in rds['lanports']:
            if rds['lanports'][item] == None:
                rds['lanports'][item] = 0
        # above for is there so the user doesn't have to fill out zeros for the types of reservations that are not needed in the RDS form
        reservation_reqs = ['SERVER']*rds['lanports']['server'] \
                         + ['PRINTER']*rds['lanports']['printer'] \
                         + ['CAMERA']*rds['lanports']['camera']
        for req in range(len(reservation_reqs)):   
            port_utilization = [len(member) for member in port_reservation]
            least_utilized_member = port_utilization.index(min(port_utilization)) # since this is a list, members are counted from 0
            port_reservation[least_utilized_member].append(reservation_reqs[req])
            print(port_reservation)
        # END: Port reservation for Printers, Cameras, Servers, etc. ----------------------------------------------------------------

        if rds['idf'][0]['switch_count'] == '0':
            mdf_access = 0
        else:
            mdf_access = 1
        
        mdf_sfp_ports = max(round(float(rds['idf'][0]['switch_count']))*4, 8*mdf_access)
        # in case of 24 port requirement in MDF, 2*24 port switches will be used in case there are less than 5 IDFs
        # therefore, minimum considered MDF SFP ports is 8
        number_of_idfs = len(rds['idf'])-1
        collapsed_distro = 0 # 0 if using distro switch, 1 if using MDF access switch for IDF uplinks
        wan_only = False # initiate wan_only variable
        # START: Distro switch MDF -----------------------------------------------------------------------------------------
        if 0 < number_of_idfs*2 <= mdf_sfp_ports and number_of_idfs < 5:
        # this if clause is for "collapsed-distro" case
            collapsed_distro = 1
            uplinks = [[] for member in range(max(round(float(rds['idf'][0]['switch_count'])), 2))]
            # above generated variable "uplinks" is a list of lists
            # number of inner lists correspond to number of member switches in MDF access switch stack
            # the items in the inner lists correspond to available SFP ports, that is 4 per stack member
            # in following part "Load balance IDF uplinks between SFP ports of MDF access switch stack" the inner lists are filled out by IDF numbers
            # e.g for 3 MDF stack members and 4 IDFs:
            # [[1, 3, 4], [1, 2, 4], [2, 3]]
            # IDF1 has uplinks in S01-1 and S01-2
            # IDF2 has uplinks in S01-2 and S01-3
            # IDF3 has uplinks in S01-1 and S01-3
            # IDF4 has uplinks in S01-1 and S01-2

            # START: Load balance IDF uplinks between SFP ports of MDF access switch stack ---------------------------------
            for _ in range(2):
                # the point of above for is to repeat the process twice for each IDF
                # at first run, first uplink for each IDF is placed
                # at second run, second uplink for each IDF is placed
                for idf in range(1,number_of_idfs+1):   
                    uplink_utilization = [len(member) for member in uplinks]
                    while True:
                        least_utilized_member = uplink_utilization.index(min(uplink_utilization)) # since this is a list, members are counted from 0
                        if idf in uplinks[least_utilized_member]:
                            uplink_utilization[least_utilized_member] = 9 # 9 serves as infinite metric here (5 would be enough, since there are 4 IDFs at most)
                        else:
                            uplinks[least_utilized_member].append(idf)
                            break
            for member in range(len(uplinks)):
                uplinks[member].sort()
            # END: Load balance IDF uplinks between SFP ports of MDF access switch stack -----------------------------------

            # START: Populate inventory details of the MDF "collapsed-distro" switch ---------------------------------------           
            inventory['distro_switch']['hw_count'] = max(round(float(rds['idf'][0]['switch_count'])), 2)
            inventory['distro_switch']['uplinks'] = ['Gi1/0/1', 'Gi2/0/1']
            inventory['connections'][2][1] = 'Gi1/0/1'
            inventory['connections'][3][1] = 'Gi2/0/1'
            
            if rds['idf'][0]['switch_count'] in ['0.55', '1']:
                inventory['distro_switch']['model'] = 'WS-C3650-24PS-S'
                inventory['distro_switch']['port_count'] = 24
            else:
                inventory['distro_switch']['model'] = 'WS-C3650-48FS-S'
                inventory['distro_switch']['port_count'] = 48
            # the aim of below for is to group the "downlinks" per IDF so the links are not crossed on map
            for idf in range(1,number_of_idfs+1):
                for member in range(len(uplinks)):
                    try:
                        port = uplinks[member].index(idf)
                    except:
                        pass
                    else:
                        inventory['distro_switch']['downlinks'].append("Gi{}/1/{}".format(str(member+1), str(port+1)))
            # END: Populate inventory details of the MDF "collapsed-distro" switch -----------------------------------------

            if rds['business_unit'] == 'bu1':
                rendered_content = render_template('configs/customer1/bu1_mdf_3650_access-distro.j2', rds=rds, date=datetime.date.today(), uplinks=uplinks, port_reservation=port_reservation)
            elif rds['business_unit'] in ['bu2', 'bu3', 'bu4']:
                rendered_content = render_template('configs/customer1/bu2-4_mdf_3650_access-distro.j2', rds=rds, date=datetime.date.today(), uplinks=uplinks, port_reservation=port_reservation)
            else:
                print('non-existent BU')
                ### redirect to error page should happen here instead of above print
        
        elif number_of_idfs > 0:
        # this elif clause is for case with dedicated distribution switch

            # START: Populate inventory details of the MDF distribution switch ---------------------------------------------
            inventory['distro_switch']['hw_count'] = 2

            if number_of_idfs < 10:
                inventory['distro_switch']['model'] = 'WS-C3850-12S-S'
                inventory['distro_switch']['port_count'] = 12
                inventory['distro_switch']['uplinks'] = ['Gi1/0/12', 'Gi2/0/12']
            else:
                inventory['distro_switch']['model'] = 'WS-C3850-24S-S'
                inventory['distro_switch']['port_count'] = 24
                inventory['distro_switch']['uplinks'] = ['Gi1/0/24', 'Gi2/0/24']

            inventory['connections'][2][1] = inventory['distro_switch']['uplinks'][0]
            inventory['connections'][3][1] = inventory['distro_switch']['uplinks'][1]
            
            # END: Populate inventory details of the MDF distribution switch -----------------------------------------------

            if rds['business_unit'] == 'bu1':
                rendered_content = render_template('configs/customer1/bu1_mdf_3850_distro.j2', rds=rds, date=datetime.date.today())
            elif rds['business_unit'] in ['bu2', 'bu3', 'bu4']:
                rendered_content = render_template('configs/customer1/bu2-4_mdf_3850_distro.j2', rds=rds, date=datetime.date.today())
                # I kept separate BU1 and BU2-4 templates for now, although they are exactly the same
            else:
                print('non-existent BU')
                ### redirect to error page should happen here instead of above print
        else:
            wan_only = True
            ### this is the case where zero LAN ports are specified
            ### such case is used when generating config for routers only, e.g. for router replacement
        if not wan_only:
            file_path = os.path.join(folder_path, "{}_S01-1_staging.txt".format(str(rds['sr_num'])))
            generated_file = open(file_path, 'w', newline="\r\n")
            generated_file.write(rendered_content)
            generated_file.close()
            # END: Distro switch MDF -------------------------------------------------------------------------------------------
            
            # START: Access switches -------------------------------------------------------------------------------------------
            skipped_switches = 0
            for idf_num in range(collapsed_distro,number_of_idfs+1): # if MDF access switch is used for IDF uplinks, its config was generated earlier in Distro part
                if rds['idf'][idf_num]['switch_count'] != '0':
                    sw_num = idf_num+2-collapsed_distro-skipped_switches

                    # START: Populate inventory details of an IDF switch ---------------------------------------------------
                    inventory['access_switches'].append({
                        'location': None,
                        'asset_id': None,
                        'name': None,
                        'model': None,
                        'port_count': None,
                        'hw_count': None,
                        'mgmt_interface': None,
                        'mgmt_ip': None,
                        'uplinks': [],
                        'downlinks': []
                    })
                    inventory['access_switches'][idf_num-collapsed_distro-skipped_switches]['asset_id'] = "{}_S{}-1".format(rds['site']['code'], str(sw_num).zfill(2))
                    inventory['access_switches'][idf_num-collapsed_distro-skipped_switches]['name'] = "{}sw{}".format(device_naming, str(sw_num).zfill(2))
                    inventory['access_switches'][idf_num-collapsed_distro-skipped_switches]['hw_count'] = round(float(rds['idf'][idf_num]['switch_count']))
                    inventory['access_switches'][idf_num-collapsed_distro-skipped_switches]['mgmt_interface'] = 'Vlan' + str(rds['vlan'][1]['vlan_id'])
                    inventory['access_switches'][idf_num-collapsed_distro-skipped_switches]['mgmt_ip'] = str(ipaddress.ip_address(rds['vlan'][1]['net'])+sw_num+4)

                    if idf_num != 0:
                        inventory['access_switches'][idf_num-collapsed_distro-skipped_switches]['location'] = 'IDF' + str(idf_num)
                    else:
                        inventory['access_switches'][idf_num-collapsed_distro-skipped_switches]['location'] = 'MDF'
                    
                    if rds['idf'][idf_num]['switch_count'] == '0.55':
                        inventory['access_switches'][idf_num-collapsed_distro-skipped_switches]['model'] = 'WS-C3650-24PS-S'
                        inventory['access_switches'][idf_num-collapsed_distro-skipped_switches]['port_count'] = 24
                    else:
                        inventory['access_switches'][idf_num-collapsed_distro-skipped_switches]['model'] = 'WS-C3650-48FS-S'
                        inventory['access_switches'][idf_num-collapsed_distro-skipped_switches]['port_count'] = 48

                    if rds['idf'][idf_num]['switch_count'] not in ['0.55', '1']:
                        inventory['access_switches'][idf_num-collapsed_distro-skipped_switches]['uplinks'] = ['Gi1/1/1', 'Gi2/1/1']
                    else:
                        inventory['access_switches'][idf_num-collapsed_distro-skipped_switches]['uplinks'] = ['Gi1/1/1', 'Gi1/1/2']

                    if idf_num != 0 and collapsed_distro == 0:
                        inventory['distro_switch']['downlinks'].append('Gi1/0/' + str(idf_num))
                        inventory['distro_switch']['downlinks'].append('Gi2/0/' + str(idf_num))
                        inventory['connections'].append(['s' + str(sw_num), inventory['access_switches'][idf_num-collapsed_distro-skipped_switches]['uplinks'][0], 's1', inventory['distro_switch']['downlinks'][(sw_num-2)*2], 'mmf'])
                        inventory['connections'].append(['s' + str(sw_num), inventory['access_switches'][idf_num-collapsed_distro-skipped_switches]['uplinks'][1], 's1', inventory['distro_switch']['downlinks'][(sw_num-2)*2+1], 'mmf'])
                    elif idf_num == 0:
                        inventory['distro_switch']['downlinks'].append('Gi1/0/' + str(inventory['distro_switch']['port_count']-1))
                        inventory['distro_switch']['downlinks'].append('Gi2/0/' + str(inventory['distro_switch']['port_count']-1))
                        inventory['connections'].append(['s' + str(sw_num), inventory['access_switches'][idf_num-collapsed_distro-skipped_switches]['uplinks'][0], 's1', inventory['distro_switch']['downlinks'][(sw_num-2)*2], 'copper'])
                        inventory['connections'].append(['s' + str(sw_num), inventory['access_switches'][idf_num-collapsed_distro-skipped_switches]['uplinks'][1], 's1', inventory['distro_switch']['downlinks'][(sw_num-2)*2+1], 'copper'])
                    elif collapsed_distro == 1:
                        inventory['connections'].append(['s' + str(sw_num), inventory['access_switches'][idf_num-collapsed_distro-skipped_switches]['uplinks'][0], 's1', inventory['distro_switch']['downlinks'][(sw_num-2)*2], 'mmf'])
                        inventory['connections'].append(['s' + str(sw_num), inventory['access_switches'][idf_num-collapsed_distro-skipped_switches]['uplinks'][1], 's1', inventory['distro_switch']['downlinks'][(sw_num-2)*2+1], 'mmf'])
                    # END: Populate inventory details of an IDF access switch ----------------------------------------------

                    if rds['business_unit'] == 'bu1':
                        rendered_content = render_template('configs/customer1/bu1_idf_3650.j2', rds=rds, date=datetime.date.today(), idf_num=idf_num, sw_num=sw_num, port_reservation=port_reservation)
                    elif rds['business_unit'] in ['bu2', 'bu3', 'bu4']:
                        rendered_content = render_template('configs/customer1/bu2-4_idf_3650.j2', rds=rds, date=datetime.date.today(), idf_num=idf_num, sw_num=sw_num, port_reservation=port_reservation)
                        # I kept separate BU1 and BU1-4 templates for now, although the difference is only a few lines in USER port config (while special port config is not part of staging)
                    else:
                        print('non-existent BU')
                        ### redirect to error page should happen here instead of above print
                    file_path = os.path.join(folder_path, "{}_S{}-1_staging.txt".format(str(rds['sr_num']), str(sw_num).zfill(2)))
                    generated_file = open(file_path, 'w', newline="\r\n")
                    generated_file.write(rendered_content)
                    generated_file.close()
                else:
                    skipped_switches += 1
            # END: Access switches -----------------------------------------------------------------------------------------

        # START: add port reservations to inventory file -------------------------------------------------------------------

        if inventory['access_switches'][0]['location'] == 'MDF':
            mdf_access_switch = 'S02'
            port_count = inventory['access_switches'][0]['port_count']
        else:
            mdf_access_switch = 'S01'
            port_count = inventory['distro_switch']['port_count']
        inventory['port_reservation'].append({mdf_access_switch: []})
        for member in range(len(port_reservation)):
            for port in range(len(port_reservation[member])):
                inventory['port_reservation'][0][mdf_access_switch].append(
                    {"Gi{}/0/{}".format(str(member+1), str(port_count-len(port_reservation[member])+port+1)): port_reservation[member][port]})

        for switch in inventory['port_reservation']:
            inventory['port_reservation_text'] = inventory['port_reservation_text'] + list(switch)[0] + r':\n'
            for reservation in switch[list(switch)[0]]:
                inventory['port_reservation_text'] = inventory['port_reservation_text'] + r' ' + list(reservation)[0] + r' - ' + reservation[list(reservation)[0]] + r'\n'

        # END: add port reservations to inventory file ---------------------------------------------------------------------

        # START: create inventory file -------------------------------------------------------------------------------------
        file_path = os.path.join(folder_path, "{}_inventory.yml".format(str(rds['sr_num'])))
        with open(file_path, 'w', newline="\r\n") as generated_file:
            yaml.dump(inventory, generated_file)
        # END: create inventory file ---------------------------------------------------------------------------------------

        # START: LE to PE --------------------------------------------------------------------------------------------------
        if collapsed_distro == 1:
            rendered_content = render_template('configs/customer1/hw_order.j2', rds=rds, device_naming=device_naming, wan_only=wan_only, collapsed_distro=collapsed_distro, uplink_utilization=[len(member) for member in uplinks])
        else:
            rendered_content = render_template('configs/customer1/hw_order.j2', rds=rds, device_naming=device_naming, wan_only=wan_only, collapsed_distro=collapsed_distro, uplink_utilization=[])
        file_path = os.path.join(folder_path, "{}_hw_order.txt".format(str(rds['sr_num'])))
        generated_file = open(file_path, 'w', newline="\r\n")
        generated_file.write(rendered_content)
        generated_file.close()
        # END: LE to PE ----------------------------------------------------------------------------------------------------
        
        # START: Implementation Plan ---------------------------------------------------------------------------------------
        rendered_content = render_template('configs/customer1/implementation_plan.j2', rds=rds, device_naming=device_naming, wan_only=wan_only, collapsed_distro=collapsed_distro)
        file_path = os.path.join(folder_path, "{}_Implementation_plan.txt".format(str(rds['sr_num'])))
        generated_file = open(file_path, 'w', newline="\r\n")
        generated_file.write(rendered_content)
        generated_file.close()
        # END: Implementation Plan -----------------------------------------------------------------------------------------

        return redirect(url_for('files', sr_num=rds['sr_num']))
    return render_template('rds-upload-customer1.html', form=form)

@app.route('/files/<int:sr_num>', methods=['GET', 'POST'])
def files(sr_num):
    staging_path = os.path.join(current_app.root_path, 'staging', 'customer1', str(sr_num))
    staging_files = os.listdir(staging_path)
    return render_template("files.html", sr_num=sr_num, staging_files=staging_files)

@app.route('/download/<int:sr_num>/<path:filename>', methods=['GET', 'POST'])
def download(sr_num, filename):
    staging_path = os.path.join(current_app.root_path, 'staging', 'customer1', str(sr_num))
    return send_from_directory(directory=staging_path, filename=filename, as_attachment=True)

@app.route('/customer1/diagram-upload', methods=['GET', 'POST'])
def diagram_upload_customer1():
    form = diagramForm()
    
    if form.validate_on_submit():
        inventory = yaml.load(form.inventory_file.data)
        folder_path = os.path.join(current_app.root_path, 'staging', 'customer1', str(inventory['sr_num']))
        os.makedirs(folder_path, exist_ok=True)
        file_path = os.path.join(folder_path, "{}_inventory.yml".format(str(inventory['sr_num'])))
        with open(file_path, 'w', newline="\r\n") as generated_file:
            yaml.dump(inventory, generated_file)
        
        return redirect(url_for('diagram_render_customer1', sr_num=inventory['sr_num']))

    return render_template('diagram-upload-customer1.html', form=form)


@app.route('/customer1/diagram-render/<int:sr_num>', methods=['GET', 'POST'])
def diagram_render_customer1(sr_num):
    inventory_path = os.path.join(current_app.root_path, 'staging', 'customer1', str(sr_num), "{}_inventory.yml".format(str(sr_num)))
    try:
        with open(inventory_path, 'r') as inventory_file:
            inventory = yaml.load(inventory_file)
    except:
        print("No inventory file in SR {} directory.".format(str(sr_num)))
        ### redirecto to error page should happen here instead of this print

    return render_template("diagram-render-customer1.html", inventory=inventory, date=datetime.date.today())

if __name__ == "__main__":
    app.run(debug=True)

