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
		return self.qr('infraCont').data.value('fbDmNm')

	@property
	def node_ids(self):
		d = self.apic.qr('fabricNode').output
		nds = [int(n) for n in d.attribute('id')]
		nds.sort()
		return nds

	@property
	def apic_ids(self):
		d = self.apic.qr('fabricNode', filter='role=controller').output
		nds = [int(n) for n in d.attribute('id')]
		nds.sort()
		return nds

	@property
	def spine_ids(self):
		d = self.apic.qr('fabricNode', filter='role=spine').output
		nds = [int(n) for n in d.attribute('id')]
		nds.sort()
		return nds

	@property
	def leaf_ids(self):
		d = self.apic.qr('fabricNode', filter='role=leaf').output
		nds = [int(n) for n in d.attribute('id')]
		nds.sort()
		return nds

	@property
	def vlans_in_use(self):
		vlans = self.qr('vlanCktEp', filter='wcard(vlanCktEp.encap, "vlan-")').data.attribute('encap')
		vlans = list(set(vlans))
		vlan_nums = [int(o[5:]) for o in vlans]
		vlan_nums.sort()
		return vlan_nums

	def node(self, id):
		address = self.qr('topSystem', filter=f'eq(topSystem.id, "{id}")').data.value('oobMgmtAddr')
		n = copy.deepcopy(self.apic)
		n.address = address
		n.fabric = self
		return n

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

	# Creates a Query object associated with the current fabric with provided parameters
	def qr(self, path=None, filter=None, target=None, target_class=None, include=None, subtree=None, subtree_class=None,
						subtree_filter=None, subtree_include=None, order=None):
		query = self.apic.qr(path=path, filter=filter, target=target, target_class=target_class, include=include,
									subtree=subtree, subtree_class=subtree_class, subtree_filter=subtree_filter,
									subtree_include=subtree_include, order=order)
		query.run()
		return query

	def remove_object(self, dn):
		js = self.qr(dn, include='naming').data.json
		js[list(js.keys())[0]]['attributes']['status'] = 'deleted'
		return self.post(js) == 200

	def aaep_cdp_neighbors(self, aaep, printout=False):
		filter = f'and(eq(l1RsAttEntityPCons.tDn, "uni/infra/attentp-{aaep}"), wcard(l1RsAttEntityPCons.dn, "phys-"))'
		q = self.qr('l1RsAttEntityPCons', filter=filter)
		neighbors = []
		for port in q.data.imdata:
			node = port['l1RsAttEntityPCons']['attributes']['dn']
			node = node[:node.find('/phys-[')]
			ifc = port['l1RsAttEntityPCons']['attributes']['parentSKey']
			qcdp = self.qr(f'{node}/cdp/inst/if-[{ifc}]', target='subtree', target_class='cdpAdjEp')
			if qcdp.count > 0:
				for nbr in qcdp.data.attribute(['devId', 'portId'], False):
					neighbors.append([node[node.find('node-')+5:node.find('/sys')], ifc, nbr[0], nbr[1]])
		if printout:
			for neighbor in neighbors:
				print(f'{neighbor[0]} {neighbor[1]} {neighbor[2]} {neighbor[3]}')
		else:
			return neighbors

	def transceiver_count(self):
		return self.apic.qr('ethpmFcot').output.sum('typeName', True)

	def change_local_user_password(self, user, old_password=None, new_password=None):
		from getpass import getpass
		if old_password is None:
			old_password = getpass('Current password: ')
		apic = node.Node(self.apic.address, f'apic#fallback\\\\{user}', old_password)
		while new_password is None:
			new_password = getpass('New password: ')
			if new_password != getpass('Re-enter new password: '):
				new_password = None
				print('Passwords do not match!')
		if apic.post({'aaaUser': {'attributes': {'dn': f'uni/userext/user-{user}', 'pwd': new_password}}}) == 200:
			print(f'Password for local account, {user}, has been changed.')
		else:
			print(apic.response.text)

	def add_epg_static(self, epg_dn, ep_net, next_hop):
		ep_net = IP(ep_net)
		if ep_net.mask is None:
			ep_net.mask = 32
		next_hop = IP(next_hop)
		for ip in ep_net.ips_in_network:
			js = {
				"fvSubnet": {
					"attributes": {
						"ctrl": "no-default-gateway",
						"dn": f"{epg_dn}/subnet-[{ip}/32]",
						"ip": f"{ip}/32",
						"preferred": "no",
						"scope": "public,shared",
						"virtual": "no"
					},
					"children": [
						{
							"fvEpReachability": {
								"attributes": {},
								"children": [
									{
										"ipNexthopEpP": {
											"attributes": {
												"nhAddr": next_hop.ip
											}
										}
									}
								]
							}
						}
					]
				}
			}
			if self.post(js) != 200:
				raise Exception(f"Addition of EPG static Endpoint Route failed. {self.apic.response.text}")
		return True

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
			qry = self.qr(cls)
			if filter is not None:
				qry.filter = filter
			for p in qry.data.imdata:
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
