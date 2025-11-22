import node               # Node object for connection to APICs, Leaves, and Spines
from ip import IP         # IP object for ipv4 address functions
import copy               # Copy object to clone class objects


class Fabric(object):
  def __init__(self, apic, username=None, password=None):
    if isinstance(apic, node.Node):
      self.__apic = apic
    else:
      self.__apic = node.Node(apic, username, password)

  @property
  def apic(self):
    return self.__apic

  @apic.setter
  def apic(self, apic):
    if isinstance(apic, node.Node):
      self.__apic = apic
    elif type(apic) is str:
      self.__apic = node.Node(apic)

  @property
  def name(self):
    return self.query('infraCont').run().value('fbDmNm')

  @property
  def node_ids(self):
    data = self.query('fabricNode').run()
    nodes = [int(n) for n in data.attribute('id')]
    nodes.sort()
    return nodes

  @property
  def apic_ids(self):
    data = self.query('fabricNode', filter='role=controller').run()
    nodes = [int(n) for n in data.attribute('id')]
    nodes.sort()
    return nodes

  @property
  def spine_ids(self):
    data = self.query('fabricNode', filter='role=spine').run()
    nodes = [int(n) for n in data.attribute('id')]
    nodes.sort()
    return nodes

  @property
  def leaf_ids(self):
    data = self.query('fabricNode', filter='role=leaf').run()
    nodes = [int(n) for n in data.attribute('id')]
    nodes.sort()
    return nodes

  @property
  def vlans_in_use(self):
    vlans = self.query('vlanCktEp', filter='wcard(vlanCktEp.encap, "vlan-")').run().attribute('encap')
    vlans = list(set(vlans))
    vlan_nums = [int(o[5:]) for o in vlans]
    vlan_nums.sort()
    return vlan_nums

  def node(self, id):
    address = self.query('topSystem', filter=f'eq(topSystem.id, "{id}")').run().value('oobMgmtAddr')
    node = copy.deepcopy(self.apic)
    node.address = address
    node.fabric = self
    return node

  # Post function used to send Post messages to fabric
  def post(self, path, payload=None):
    return self.apic.post(path, payload)

  def login(self, user=None, password=None):
    return self.apic.login(user, password)

  # Creates a Query object associated with the current fabric with provided parameters
  def query(self, path=None, filter=None, target=None, target_class=None, include=None, subtree=None, subtree_class=None,
            subtree_filter=None, subtree_include=None, order=None):
    return self.apic.query(path=path, filter=filter, target=target, target_class=target_class, include=include,
                  subtree=subtree, subtree_class=subtree_class, subtree_filter=subtree_filter,
                  subtree_include=subtree_include, order=order)
  
  # Create and hrun a query, equivalent to query(params).run()
  def qr(self, *args, **kwargs):
    return self.query(*args, **kwargs).run()

  # Trigger ACI to remove an object indicated by dn
  def remove_object(self, dn):
    payload = self.query(dn, include='naming').run().json
    payload[list(payload.keys())[0]]['attributes']['status'] = 'deleted'
    return self.post(payload) == 200
  
# Pull a list of packets/frames seen by the fabric
  def packets(self, ip=None, tenant=None, port=None, action=None, window_start=None, window_end=None):
    pkts = []
    filter_list = []
    if action is not None:
      if action not in ['Permit', 'Drop']:
        raise Exception('Invalid action. Possible values are Permit and Drop.')
      action = [action]
    else:
      action = ['Permit', 'Drop']
    for act in action:
      cls = f'acllog{act}L3Pkt'
      if ip is not None:
        if '/' in ip:
          filter_list.append(f'or(wcard({cls}.srcIp, "{ip}"), wcard({cls}.dstIp, "{ip}"))')
        else:
          filter_list.append(f'or(eq({cls}.srcIp, "{ip}"), eq({cls}.dstIp, "{ip}"))')
      if tenant is not None:
        filter_list.append(f'wcard({cls}.dn, "/tn-{tenant}/")')
      if port is not None:
        filter_list.append(f'or(eq({cls}.srcPort, "{port}"), eq({cls}.dstPort, "{port}"))')
      if window_start is not None:
        filter_list.append(f'gt({cls}.timeStamp, "{window_start}")')
      if window_end is not None:
        filter_list.append(f'gt({cls}.timeStamp, "{window_end}")')
      if len(filter_list) == 0:
        filter = None
      else:
        filter = filter_list[0]
        if len(filter_list) > 1:
          for o in filter_list[1:]:
            filter += ',' + o
          filter = f'and({filter})'
      data = self.query(cls, filter=filter)
#      qry = self.query(cls)
#      if filter is not None:
#        qry.filter = filter
      for p in data.imdata:
        dn = p[cls]['attributes']['dn']
        js = {
          'action': act.lower(),
          'node': dn[:dn.find('/ndbgs/')],
          'vrf': dn[dn.find('/acllog/')+8:dn.find(f'/{act.lower()}l3')],
          'vrfEncap': p[cls]['attributes']['vrfEncap'],
          'protocol': p[cls]['attributes']['protocol'],
          'length': int(p[cls]['attributes']['pktLen']),
          'timestamp': p[cls]['attributes']['timeStamp'],
          'src': {
            'epgName': p[cls]['attributes']['srcEpgName'],
            'interface': p[cls]['attributes']['srcIntf'],
            'ip': p[cls]['attributes']['srcIp'],
            'mac': p[cls]['attributes']['srcMacAddr'],
            'pcTag': int(p[cls]['attributes']['srcPcTag']),
            'port': p[cls]['attributes']['srcPort']
          },
          'dst': {
            'epgName': p[cls]['attributes']['dstEpgName'],
            'ip': p[cls]['attributes']['dstIp'],
            'mac': p[cls]['attributes']['dstMacAddr'],
            'pcTag': int(p[cls]['attributes']['dstPcTag']),
            'port': p[cls]['attributes']['dstPort']
          }
        }
        pkts.append(js)
    return pkts
  
  # Provide a list of trancievers connected to leaves in the fabric
  def transceiver_count(self):
    return self.query('ethpmFcot').run().sum('typeName', True)
