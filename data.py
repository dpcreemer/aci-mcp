import json


def json_to_xml(js, key=None, indent=0):
	if key is None:
		if type(js) is list:
			rv = ''
			for o in js:
				key = list(o.keys())[0]
				rv += json_to_xml(o[key], key)
			return rv
		elif 'imdata' in js:
			key = 'imdata'
		else:
			key = list(js.keys())[0]
			js = js[key]
	if key == 'imdata' and 'totalCount' in js:
		atts = f' totalCount="{js["totalCount"]}"'
		sub = ''
		for o in js['imdata']:
			subkey = str(list(o.keys())[0])
			sub += json_to_xml(o[subkey], subkey, indent + 2)
		return f'<{key}{atts}>\n{sub}</{key}>\n'
	elif 'attributes' in js:
		atts = ''
		for att in js['attributes'].keys():
			atts += f" {att}='{js['attributes'][att]}'"
		if 'children' in js:
			sub = ''
			for o in js['children']:
				subkey = str(list(o.keys())[0])
				sub += json_to_xml(o[subkey], subkey, indent + 2)
			return ' ' * indent + f'<{key}{atts}>\n{sub}</{key}>\n'
		else:
			return ' ' * indent + f'<{key}{atts}/>\n'
	else:
		print('fault')


# split string into a list at each occurrence of split_char ignoring an occurrence of the split_char within a quotes.
def split_unquoted(source_string, split_char):
	return_value = []
	pos = source_string.find(split_char)
	while pos >= 0:
		if source_string[:pos].count('\"') % 2 == 1:
			pos = source_string.find(split_char, pos+1)
		else:
			return_value.append(source_string[:pos])
			source_string = source_string[pos+1:]
			pos = source_string.find(split_char)
	return_value.append(source_string)
	return return_value


# Pulls the first full XML entry, including all children, from an xml string.
def xml_item(xml):
	xml = xml.strip()
	if not xml[:1] == '<':
		raise Exception(f'Invalid Character found in xml string, "{xml}".  XML should start with "<"')
	item = xml[:xml.find('>')+1]
	if item[-2] != "/":
		key = item[1:item.find(' ')]
		item = xml[:xml.find(f'</{key}>')+len(f'<{key}>')+1]
	return item


# convert XML entry to json
def xml_entry_to_json(xml):
	xml = xml[1:-2]if xml[-2:] == "/>" else xml[1:-1]
	parts = split_unquoted(xml, " ")
	js = {parts[0]: {'attributes': {}}}
	for o in parts[1:]:
		js[parts[0]]['attributes'][o[:o.find('=')]] = o[o.find('=')+1:][1:-1]
	return js


# convert XML to JSON
def xml_to_json(xml):
	if xml[:5] == '<?xml':
		xml = xml[xml.find('?>')+2:]
	if 'imdata' in xml[:8]:
		body = xml[xml[1:].find('<')+1:xml[:-1].rfind('>')+1]
		total_count = xml[xml.find('=')+2:xml.find('\">')]
		return {'totalCount': str(total_count), 'imdata': xml_to_json(body)}
	rv = []
	while len(xml) > 0:
		item = xml_item(xml)
		xml = xml[len(item):].strip()
		if item.find('>') < len(item) -1:
			hdr = item[:item.find('>')+1]
			body = item[len(hdr):item.find(f'</{hdr[1:hdr.find(" ")]}>')]
			js = xml_entry_to_json(hdr)
			js[list(js.keys())[0]]['children'] = xml_to_json(body)
		else:
			js = xml_entry_to_json(item)
		rv.append(js)
	return rv if len(rv) > 1 else rv[0]


class Data(object):
	def __init__(self, content):
		if type(content) is str:
			content = content.strip()
			if content[0] == '<':
				content = xml_to_json(content)
			else:
				content = json.loads(content)
		self.__content = content

	@property
	def content(self):
		return self.__content

	@property
	def json(self):
		return self.imdata

	@property
	def xml(self):
		return json_to_xml(self.content)

	@property
	def imdata(self):
		if type(self.content) is dict:
			if 'imdata' in self.content:
				return self.content['imdata']
			return [self.content]
		return self.content

	@property
	def count(self):
		if type(self.content) is dict:
			if 'totalCount' in self.content:
				return int(self.content['totalCount'])
			else:
				return 1
		elif type(self.content) is list:
			return len(self.content)

	def attribute(self, attribute, keys=False):
		if type(attribute) is str:
			return [o[list(o)[0]]['attributes'][attribute] for o in self.imdata]
		elif type(attribute) is list:
			lst = []
			for o in self.imdata:
				if keys:
					sub = {a: o[list(o.keys())[0]]['attributes'][a] for a in attribute}
				else:
					sub = [o[list(o.keys())[0]]['attributes'][a] for a in attribute]
				lst.append(sub)
			return lst
		else:
			raise Exception('Invalid attribute type.  Must be String or List.')

	def value(self, attribute):
		value = self.attribute(attribute)
		if len(value) == 0:
			return None
		return value[0]

	def sum(self, attribute, printout=False, minimum=0):
		ret = {}
		for val in self.attribute(attribute):
			ret[val] = ret[val]+1 if val in ret else 0
		for val in list(ret.keys()):
			if ret[val] < minimum:
				_ = ret.pop(val)
		if printout:
			for val in ret:
				if ret[val] > minimum:
					print(f'{val}: {ret[val]}')
		else:
			return ret

	def print(self, index=None, style='json'):
		if index is not None:
			if type(index) is not int:
				raise Exception('Invalid index.  Must be an integer value')
			if not 0 <= index < self.count:
				raise Exception('Invalid index.  Input is out of bounds of output array.')
		if style == 'json':
			if index is None:
				print(json.dumps(self.json, indent=2))
			else:
				print(json.dumps(self.imdata[index], indent=2))
		elif style == 'xml':
			if index is None:
				print(self.xml)
			else:
				print(json_to_xml(self.imdata[index]))
		else:
			print(self.content)

	def save(self, filename, index=None, style='json'):
		if index is None and self.count == 1:
			index = 0
		else:
			if type(index) is not int:
				raise Exception('Invalid index.  Must be an integer value')
			if not 0 <= index < self.count:
				raise Exception('Invalid index.  Out of bounds of output array.')
		if style == 'xml':
			if index is None:
				out = self.xml
			else:
				out = self.json_to_xml(self.imdata[index])
		else:
			if index is None:
				out = json.dumps(self.imdata, indent=2)
			else:
				out = json.dumps(self.imdata[index], indent=2)
		file = open(filename, 'w')
		file.write(out)
		file.close()
