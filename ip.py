import socket
gateway_standard_default = 'last'


def valid_ip(ip):
	if type(ip) == str:
		if not ip.replace('.', '').isdigit():
			raise Exception('Invalid character in ip.')
		if ip.count('.') != 3:
			Exception('Invalid ip format.')
		for oct in ip.split('.'):
			if not 0 <= int(oct) < 256:
				raise Exception('Invalid octet in ip.')
	elif type(ip) == int:
		if not 0 <= ip < pow(2, 32):
			raise Exception('Invalid decimal ip value.')
	else:
		raise Exception('Input ip is not a valid type.')


def is_ip(address):
	if not address.replace('.', '').replace('/', '').isdigit():
		return False
	ip = address[:address.find('/')] if '/' in address else address
	try:
		valid_ip(ip)
	except:
		return False
	return True


# Convert between string and decimal IP.
def decimal(ip):
	if isinstance(ip, IP):
		ip = ip.ip
	if type(ip) == str and '/' in ip:
		ip = ip[:ip.find('/')]
	valid_ip(ip)
	if type(ip) == int:
		rv = ''
		while ip > 0:
			rv = str(ip % 256) + "." + rv
			ip = int(ip / 256)
		return rv[:-1]
	else:
		rv = 0
		for octet in ip.split('.'):
			rv *= 256
			rv += int(octet)
		return rv


# IP object provide IPv4 address testing/manipulation
#   ip is a ip address in a string variable with our without CIDR mask
#      or ip can be a ip address in decimal form
#   mask is a string containing a subnet mask in dotted notation e.g. 255.255.255.0
#      or mask can be a string or int value CIDR mask 0-32
class IP(object):
	def __init__(self, address, mask=None):
		self.__mask = None
		self.__address = None
		self.__ip = None
		self.__gateway_standard = None
		self.address = address
		self.gateway_standard = gateway_standard_default
		if mask is not None:
			self.mask = mask

	@property
	def address(self):
		return self.__address

	@address.setter
	def address(self, address):
		if is_ip(address):
			self.ip = address
		else:
			try:
				self.ip = socket.gethostbyname(address)
			except socket.gaierror:
				raise Exception(f'Unable to resolve hostname, {address}.')
		self.__address = address

	@property
	def ip(self):
		return self.__ip

	@ip.setter
	def ip(self, ip):
		if type(ip) == str:
			if '/' in ip:
				self.mask = ip[ip.find('/')+1:]
				ip = ip[:ip.find('/')]
			valid_ip(ip)
		if type(ip) == int:
			ip = decimal(ip)
		self.__ip = ip

	@property
	def cidr(self):
		ip = self.ip
		if self.mask is None:
			raise Exception('IP has no mask.  CIDR not possible.')
		else:
			return ip + '/' + str(self.mask)

	@cidr.setter
	def cidr(self, ip):
		if isinstance(ip, IP):
			self.ip = ip.cidr
		elif type(ip) != str or '/' not in ip:
			raise Exception('Invalid input.  No subnet info provided.')
		else:
			self.ip = ip

	@property
	def mask(self):
		return self.__mask

	@mask.setter
	def mask(self, mask):
		if mask is None:
			self.__mask = None
		elif type(mask) is str:
			if mask.isdigit():
				if not 0 <= int(mask) <= 32:
					raise Exception('Mask out of range. Must be between /0 and /32.')
				mask = int(mask)
			else:
				n = decimal(mask)
				i = 0
				while n > 0:
					n -= pow(2, 31-i)
					i += 1
				if not n == 0:
					raise Exception('%s is not a valid subnet mask.' % mask)
				mask = i
		elif type(mask) == int:
			if not 0 <= mask <= 32:
				raise Exception('Mask out of range. Must be between /0 and /32.')
		else:
			raise Exception('Invalid type for mask. Must be int or str.')
		self.__mask = mask

	@property
	def gateway_standard(self):
		return self.__gateway_standard

	@gateway_standard.setter
	def gateway_standard(self, standard):
		if type(standard) is not str:
			raise Exception(f'Invalid gateway standard type.  {type(standard)} provided.  Should be string.')
		standard = standard.lower()
		if standard not in ['first', 'last']:
			raise Exception(f'Invalid gateway standard. {standard} provided. Should be "first" or "last".')
		self.__gateway_standard = standard

	@property
	def subnet(self):
		if self.mask is None:
			return None
		d = self.dec
		return decimal(d - (d % pow(2, 32-self.mask))) + '/' + str(self.mask)

	@property
	def broadcast(self):
		if self.mask is None:
			return None
		d = self.dec
		sz = pow(2, 32-self.mask)
		return decimal(d - (d % sz) + sz - 1)

	@property
	def gateway(self):
		if self.mask is None:
			return None
		if self.gateway_standard == 'last':
			return decimal(decimal(self.broadcast)-1)
		return decimal(decimal(self.subnet)+1)

	@property
	def is_subnet(self):
		if self.subnet == self.cidr:
			return True
		return False

	@property
	def is_gateway(self):
		if self.gateway == self.ip:
			return True
		return False

	@property
	def dec(self):
		return decimal(self.ip)

	@property
	def ips_in_network(self):
		if self.mask is None:
			return self.ip
		base = decimal(self.subnet)
		return [decimal(base + i) for i in range(2**(32-self.mask))]

	def __add__(self, val):
		if type(val) == int:
			ip = decimal(self.ip) + val
			return IP(ip, self.mask)

	def __sub__(self, val):
		if type(val) == int:
			ip = decimal(self.ip) - val
			return IP(ip, self.mask)
		if isinstance(val, IP):
			return decimal(self.ip) - decimal(val.ip)

	def __contains__(self, val):
		subd = decimal(self.subnet[:self.subnet.find('/')])
		if isinstance(val, IP):
			val = decimal(val.ip)
		elif type(val) is str:
			val = decimal(val)
		else:
			return False
		return 0 <= val - subd < pow(2, 32 - self.mask)
