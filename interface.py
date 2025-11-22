class Interface(object):
	def __init__(self, node, interface):
		self.__node = node
		self.__id = None
		self.__dn = None
		self.__type = None
		self.id = interface

	@property
	def node(self):
		return self.__node

	@property
	def id(self):
		return self.__id

	@id.setter
	def id(self, interface):
		if type(interface) is int:
			interface = f'eth1/{interface}'
		if type(interface) is str:
			if interface.isdigit():
				interface = f'eth1/{interface}'
			else:
				interface = interface.lower().replace('ethernet', 'eth')
		else:
			raise Exception(f'Invalid interface, {interface}, provided.')
		d = self.__node.qr('l1PhysIf', filter=f'eq(l1PhysIf.id, "{interface}"').data
		if d.count != 1:
			raise Exception(f'Interface {interface} was not found on {self.__node.name}.')
		self.__id = interface
		self.__dn = d.value('dn')
		self.__type = d.value('portT')

	@property
	def admin_state(self):
		return self.node.qr(self.dn).data.value('adminSt')

	@admin_state.setter
	def admin_state(self, state):
		if state not in ['up', 'down']:
			raise Exception(f'Invalid Interface Admin State {state}.  Valid options are "up" and "down".')
		js = {
			'l1PhysIf': {
				'attributes': {
					'dn': f'topology/pod-{self.node.pod}/node-{self.node.id}/{self.dn}',
					'adminSt': state
				}
			}
		}
		self.node.fabric.post(js)

	@property
	def state(self):
		return self.node.qr(f'{self.dn}/phys').data.value('operSt')

	@property
	def speed(self):
		return self.node.qr(self.dn).data.value('speed')

	@property
	def oper_speed(self):
		return self.node.qr(f'{self.dn}/phys').data.value('operSpeed')

	@property
	def dn(self):
		return self.__dn

	@property
	def type(self):
		return self.__type

	@property
	def crc_errors(self):
		return int(self.node.qr(f'{self.dn}/dbgEtherStats').data.value('cRCAlignErrors'))

	@property
	def packets(self):
		return int(self.node.qr(f'{self.dn}/dbgEtherStats').data.value('pkts'))

	@property
	def packets_in(self):
		packet_data = self.node.qr(f'{self.dn}/dbgIfIn').data
		return int(packet_data.value('ucastPkts')) + int(packet_data.value('nUcastPkts'))

	@property
	def packets_out(self):
		packet_data = self.node.qr(f'{self.dn}/dbgIfOut').data
		return int(packet_data.value('ucastPkts')) + int(packet_data.value('nUcastPkts'))

	@property
	def input_errors(self):
		return int(self.node.qr(f'{self.dn}/dbgIfIn').data.value('errors'))

	@property
	def output_errors(self):
		return int(self.node.qr(f'{self.dn}/dbgIfOut').data.value('errors'))

	@property
	def packet_data(self):
		data = self.node.qr(self.dn, target='children', target_class='rmonEtherStats,rmonIfIn,rmonIfOut').data
		pkt_data = {list(o.keys())[0]: o[list(o.keys())[0]] for o in data.imdata}
		return {
			'packets': int(pkt_data['rmonEtherStats']['attributes']['pkts']),
			'packets_in': int(pkt_data['rmonIfIn']['attributes']['ucastPkts']) + int(pkt_data['rmonIfIn']['attributes']['nUcastPkts']),
			'packets_out': int(pkt_data['rmonIfOut']['attributes']['ucastPkts']) + int(pkt_data['rmonIfOut']['attributes']['nUcastPkts']),
			'crc_errors': int(pkt_data['rmonEtherStats']['attributes']['cRCAlignErrors']),
			'input_errors': int(pkt_data['rmonIfIn']['attributes']['errors']),
			'output_errors': int(pkt_data['rmonIfOut']['attributes']['errors'])
		}
