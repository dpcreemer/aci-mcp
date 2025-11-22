import requests  # Requests module used for Rest API calls
from datetime import datetime  # datetime module for date/time manipulation
import json      # JSON module for interacting with JSON formatted data

from query import Query   # Query module provides logic to manage REST API queries
from data import Data
from ip import IP
from interface import Interface
import fabric


# Fabric object used to interact with an ACI fabric.
# Initialized with a "address" property, the management address of a fabric APIC
# Optional username and password properties allow for authentication
class Node(object):
  def __init__(self, address, username=None, password=None, parent_fabric=None, auto_login=True):
    self.__ip = None
    self.__address = None
    self.__username = None
    self.__password = None
    self.__fabric = parent_fabric
    self.__dn = None
    self.__id = None
    self.__pod = None
    self.__name = None
    self.__role = None
    self.__cookies = ''
    self.__auto_login = auto_login
    self.username = username
    self.password = password
    self.established = 0
    requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
    self.session = requests.session()
    self.response = None
    self.address = address

  @property
  def address(self):
    return self.__address

  @address.setter
  def address(self, address):
    if self.__address is not None and self.__address != self.address:
      self.__clear_values()
    self.__address = address
    self.ip = address
    if not self.check_connection():
      raise Exception(f'Unable to connect to {address}.')

  @property
  def ip(self):
    return self.__ip

  @ip.setter
  def ip(self, address):
    if isinstance(address, IP):
      self.__ip = address
    else:
      self.__ip = IP(address)

  @property
  def cookies(self):
    return self.__cookies

  @cookies.setter
  def cookies(self, cookies):
    if type(cookies) is str:
      self.session.cookies.set('APIC-cookie', cookies)
      self.__cookies = self.session.cookies
    else:
      self.__cookies = cookies

  @property
  def fabric(self):
    return self.__fabric

  @fabric.setter
  def fabric(self, fab):
    if not isinstance(fab, fabric.Fabric):
      raise Exception(f'Fabric must be a Fabric object. {type(fab)} provided.')
    self.__fabric = fab

  @property
  def dn(self):
    if self.__dn is None:
      self.__init_values()
    return self.__dn

  @property
  def id(self):
    if self.__dn is None:
      self.__init_values()
    return self.__id

  @property
  def pod(self):
    if self.__dn is None:
      self.__init_values()
    return self.__pod

  @property
  def name(self):
    if self.__dn is None:
      self.__init_values()
    return self.__name

  @property
  def role(self):
    if self.__dn is None:
      self.__init_values()
    return self.__role

  @property
  def auto_login(self):
    return self.__auto_login

  @auto_login.setter
  def auto_login(self, auto_login):
    if type(auto_login) is not bool:
      raise Exception('auto_login: Invalid value. Must by type boolean.')
    self.__auto_login = auto_login

  @property
  def login_status(self):
    self.__get('mo/topology/pod-1/node-1.json')
    return self.response.status_code != 403

  @property
  def username(self):
    return self.__username

  @username.setter
  def username(self, username):
    if username in ['', None]:
      self.__username = None
    elif type(username) is str:
      self.__username = username
    else:
      raise Exception('Invalid username. Must be a string.')

  @property
  def password(self):
    return None

  @password.setter
  def password(self, password):
    if password in ['', None]:
      self.__password = None
    elif type(password) is str:
      self.__password = password
    else:
      raise Exception('Invalid password. Must be a string or None.')

  @property
  def interfaces(self):
    return self.query('l1PhysIf').run().attribute('id')

  def __clear_values(self):
    self.__dn = None
    self.__id = None
    self.__pod = None
    self.__name = None
    self.__role = None

  def __init_values(self):
    d = self.query('topSystem', filter=f'eq(topSystem.oobMgmtAddr, "{self.ip.ip}")').run()
    self.__dn = d.value('dn')
    self.__id = int(d.value('id'))
    self.__pod = int(d.value('podId'))
    self.__name = d.value('name')
    self.__role = d.value('role')

  def copy(self):
    import copy   # copy module for copy of class object
    return copy.deepcopy(self)

  def password_prompt(self):
    import getpass    # GetPass module used for obfuscated password input
    self.__password = getpass.getpass("Password: ")

  def clear_credentials(self):
    self.username = None
    self.password = None

  # Check connection to fabric.
  def check_connection(self):
    try:
      _ = requests.get(f'https://{self.address}/', timeout=5, verify=False)
    except requests.ConnectionError:
      return False
    return True

  # Login function sends login request to APIC and, on success, populates cookies and established variables
  # Returns boolean of login success
  def login(self, username=None, password=None):
    if username is not None:
      self.username = username
    if password is not None:
      self.__password = password
    if self.username is None or self.username == '':
      self.username = input("Username: ")
    if self.__password is None:
      self.password_prompt()
    js = {'aaaUser': {'attributes': {'name': self.username, 'pwd': self.__password}}}
    self.__post('aaaLogin.json', js)
    if self.response.status_code == 401:
      print("Authentication failed.")
      self.clear_credentials()
      return False
    if self.response.status_code >= 400:
      raise Exception(f"Error {self.response.status_code} - HTTPS Request Error - Abort!")
    self.__cookies = self.response.cookies
    self.established = datetime.now()
    return True

  # Refresh function sends a session refresh request to APIC.
  # Returns boolean of refresh success
  def refresh(self):
    self.__post('/mo/aaaRefresh.json', {})
    if self.response.status_code >= 400:
      print(f"Error {self.response.status_code} - Unable to refresh session - ABORT!")
      return False
    self.__cookies = self.response.cookies
    return True

  # Logout function sends a logout request to APIC
  # Returns boolean of logout success
  def logout(self):
    payload = {'aaaUser': {'attributes': {'name': self.username}}}
    self.__post('/mo/aaaLogout.json', payload)
    if self.response.status_code >= 400:
      print(f"Error {self.response.status_code} - HTTPS Request Error - ABORT!")
      return False
    self.established = 0
    self.__password = None
    return True

  # private post function to do the real post work
  #  Path - url path (past https://<ip>/api/)
  #  Payload - The data to be posted to fabric
  def __post(self, path, payload):
    js = json.dumps(payload)
    url = f"https://{self.address}/api/{path}"
    try:
      self.response = self.session.post(url, data=js, cookies=self.cookies, verify=False)
    except Exception as e:
      print(f"Post failed. Exception {e}")
      return False
    return True

  # Post function used to send Post messages to fabric
  def post(self, path, payload=None):
    if payload is None:
      payload = path
      path = 'mo.json'
      if type(payload) is str and payload.strip()[0] == '<':
        path = 'mo.xml'
    if isinstance(payload, Data):
      payload = payload.json
    self.__post(path, payload)
    if self.response.status_code == 403:
      if self.auto_login:
        if not self.login():
          raise Exception('Authentication failed.')
        self.__post(path, payload)
      else:
        raise Exception('Unable to post to node. Not currently logged in and "auto_login" is disabled.')
    return self.response.status_code

  # Post config from a file to the apic
  def post_file(self, filename, variables=None):
    cfg = open(filename).read()
    if type(variables) is dict:
      for key in variables:
        cfg = cfg.replace('{{' + key + '}}', variables[key])
    if filename[filename.rfind('.'):] in ['.xml', '.json']:
      file_type = filename[filename.rfind('.')+1:]
    else:
      if cfg.count('<') + cfg.count('>') > cfg.count('{') + cfg.count('}'):
        file_type = 'xml'
      else:
        file_type = 'json'
    if file_type not in ['xml', 'json']:
      raise Exception('Invalid file type.  Valid options are "json" and "xml".')
    if file_type == 'json':
      cfg = json.loads(cfg)
      self.post('mo.json', cfg)
    elif file_type == 'xml':
      if cfg.count('\"') > cfg.count('\''):
        cfg = cfg.replace('\"', '\'')
      self.post('mo.xml', cfg)
      if not self.response.status_code == 200:
        print(self.response.text)
    return self.response.status_code == 200

  # private get function to do the real get work
  #  Path - url path (past https://<ip>/api/)
  #  Parameters - Parameters to be passed to ACI with the Get request
  def __get(self, path, parameters=None):
    url = f"https://{self.address}/api/{path}"
    try:
      self.response = self.session.get(url, params=parameters, cookies=self.cookies, verify=False)
    except Exception as e:
      print(f"Query failed. Exception {e}")
      return False
    return True

  # Query fabric
  #  Path - url path
  #  Parameters - query parameters
  def get(self, path, parameters=None):
    self.__get(path, parameters)
    if self.response.status_code == 403:
      if self.auto_login:
        self.login()
        self.__get(path, parameters)
      else:
        raise Exception('Unable to query node. Not currently logged in and "auto_login" is disabled.')
    if path[-5:] == '.json':
      return json.loads(self.response.text)
    return self.response.text

  # Creates a Query object associated with the current fabric with provided parameters
  def query(self, path=None, filter=None, target=None, target_class=None, include=None, subtree=None, subtree_class=None,
            subtree_filter=None, subtree_include=None, order=None):
    return Query(self, path=path, filter=filter, target=target, target_class=target_class, include=include,
                  subtree=subtree, subtree_class=subtree_class, subtree_filter=subtree_filter,
                  subtree_include=subtree_include, order=order)
  
  # Creates a Querry object and runs it 
  def qr(self, *args, **kwargs):
    return self.query(*args, **kwargs).run()

  # Checks to see if an object exists with the provided dn
  def exists(self, dn):
    if not type(dn) == str:
      if hasattr(dn, 'dn'):
        dn = dn.dn
    else:
      raise Exception('Invalid object type.  Must be string or a class object with a dn property.')
    data = self.query(dn, include='naming-only').run()
    if data.count == '0':
      return False
    if 'error' in data.imdata[0].keys():
      return False
    return True

  # return the class of an object from its dn
  def get_class(self, dn):
    dn = dn.lstrip('mo/').rstrip('.json').rstrip('.xml')
    if not self.exists(dn):
      raise Exception('%s does not exist or is not a valid dn.' % dn)
    data= self.query('mo/%s.json' % dn).run()
    return list(data.imdata[0].keys())[0]

  def remove_object(self, dn):
    js = self.query(dn, include='naming').run().imdata[0]
    js[list(js.keys())[0]]['attributes']['status'] = 'deleted'
    self.post(js)
    if self.response.status_code != 200:
      print(self.response.text)

  def interface(self, ifc):
    return Interface(self, ifc)

  def cdp_neighbors(self, ifc=None):
    if ifc is None:
      nbrs = self.query('cdpAdjEp').run()
    else:
      ifc = Interface(self, ifc)
      nbrs = self.query(f'{self.dn}/cdp/inst/if-[{ifc.id}]', target='subtree', target_class='cdpAdjEp').run()
    nbrs = nbrs.attribute(['dn', 'devId', 'portId'], keys=True)
    lst = []
    for d in nbrs:
      if 'node-' in d['dn']:
        node = d['dn'].split('/')[2].strip('node-')
      else:
        node = self.id
      js = {
        'node': str(node),
        'nodeifc': d['dn'][d['dn'].find('if-[')+4:d['dn'].rfind(']')],
        'neighbor': d['devId'],
        'neighborifc': d['portId']
      }
      lst.append(js)
    return lst

  def lldp_neighbors(self, ifc=None):
    if ifc is None:
      nbrs = self.query('lldpAdjEp').run()
    else:
      ifc = Interface(self, ifc)
      nbrs = self.query(f'{self.dn}/lldp/inst/if-[{ifc.id}]', target='subtree', target_class='lldpAdjEp').run()
    nbrs = nbrs.attribute(['dn', 'sysName', 'portIdV'], True)
    lst = []
    for d in nbrs:
      if 'node-' in d['dn']:
        node = d['dn'].split('/')[2].strip('node-')
      else:
        node = self.id
      js = {
        'node': str(node),
        'nodeifc': d['dn'][d['dn'].find('[')+1:d['dn'].find(']')],
        'neighbor': d['sysName'],
        'neighborifc': d['portIdV']
      }
      lst.append(js)
    return lst
