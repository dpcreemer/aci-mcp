import node
import json
import data


# Query object used to create, manage, and review a fabric/leaf/spine query
class Query(object):
	def __init__(self, the_node, path=None, target=None, target_class=None, filter=None, include=None, subtree=None,
								subtree_class=None, subtree_filter=None, subtree_include=None, order=None):
		self.__node = None
		self.__path = None
		self.__target = None
		self.__target_class = None
		self.__filter = None
		self.__include = None
		self.__subtree = None
		self.__subtree_class = None
		self.__subtree_filter = None
		self.__subtree_include = None
		self.__order = None
		self.__data = None
		self.parameters = None
		self.node = the_node
		self.path = path
		self.target = target
		self.target_class = target_class
		self.filter = filter
		self.include = include
		self.subtree = subtree
		self.subtree_class = subtree_class
		self.subtree_filter = subtree_filter
		self.subtree_include = subtree_include
		self.order = order

	@property
	def node(self):
		return self.__node

	@node.setter
	def node(self, the_node):
		if not isinstance(the_node, node.Node):
			raise Exception("Fabric parameter must be on object of the Fabric class.")
		self.__node = the_node

	@property
	def path(self):
		if self.__path is None:
			return None
		return self.__path+'.json'

	@path.setter
	def path(self, path):
		if path == '':
			path = None
		if path is not None:
			if type(path) is not str:
				raise Exception('Invalid type for path.  Should be string.')
			if path[:path.find('/')+1] not in ['mo/', 'class/']:
				if path.find('/') > 0:
					path = 'mo/'+path
				else:
					path = 'class/'+path
			if path[path.rfind('.'):] == '.json':
				path = path[:path.rfind('.json')]
		if not self.__path == path:
			self.__data = None
		self.__path = path

	@property
	def data(self):
		return self.__data

	@property
	def count(self):
		return self.__data.count

	@property
	def output(self):
		return self.__data

	@property
	def output_class(self):
		if self.path[:6] == 'class/':
			return self.path.lstrip('class/').rstrip('.json').rstrip('.xml')
		else:
			return self.node.get_class(self.path)

	@property
	def target(self):
		return self.__target

	@target.setter
	def target(self, target):
		if target not in [None, 'self', 'children', 'subtree']:
			raise Exception("Invalid query target.  Options are self, children, and subtree.")
		self.__target = target.lower() if type(target) is str else target

	@property
	def target_class(self):
		return self.__target_class

	@target_class.setter
	def target_class(self, target_class):
		if not (target_class is None or type(target_class) is str):
			raise Exception('Invalid target class provided.  Must be of type str or None.')
		self.__target_class = target_class

	@property
	def filter(self):
		return self.__filter

	@filter.setter
	def filter(self, filter):
		if not (filter is None or type(filter) == str):
			raise Exception('Invalid filter provided.  Must be of type str or None.')
		self.__filter = filter
		if type(filter) == str and filter.count('=') == 1:
			self.__filter = f'eq({self.output_class}.{filter.split("=")[0]}, "{filter.split("=")[1].lstrip()}")'

	@property
	def include(self):
		return self.__include

	@include.setter
	def include(self, include):
		if type(include) == str:
			if include.lower() in ['name', 'naming']:
				include = 'naming-only'
			if include.lower() in ['config']:
				include = 'config-only'
		if include not in [None, 'all', 'naming-only', 'config-only']:
			raise Exception('Invalid prop_include option.  Valid options are None, "all", "naming-only", "config-only".')
		self.__include = include

	@property
	def subtree(self):
		return self.__subtree

	@subtree.setter
	def subtree(self, subtree):
		if subtree in [True, 'true']:
			subtree = 'full'
		if subtree not in [None, 'no', 'children', 'full']:
			raise Exception('Invalid query response sub.  Options are no, children, and full.')
		self.__subtree = subtree

	@property
	def subtree_class(self):
		return self.__subtree_class

	@subtree_class.setter
	def subtree_class(self, subtree_class):
		if subtree_class in ['', None]:
			self.__subtree_class = None
		elif type(subtree_class) is not str:
			raise Exception('Invalid subtree class provided.  Must be string or none.')
		else:
			self.__subtree_class = subtree_class

	@property
	def subtree_filter(self):
		return self.__subtree_filter

	@subtree_filter.setter
	def subtree_filter(self, subtree_filter):
		if subtree_filter == '':
			self.__subtree_filter = None
		if not (subtree_filter is None or type(subtree_filter) is str):
			raise Exception('Invalid subtree filter.  Must be type String or None.')
		self.__subtree_filter = subtree_filter

	@property
	def subtree_include(self):
		return self.__subtree_include

	@subtree_include.setter
	def subtree_include(self, subtree_include):
		if type(subtree_include) == str:
			if ',' in subtree_include:
				inc = subtree_include.split(',')[0]
				opt = subtree_include.split(',')[1]
			else:
				inc = subtree_include
				opt = None
			if inc not in ['faults', 'health', 'stats', 'fault-records', 'health-records', 'audit-logs', 'event-logs',
										'relations', 'relations-with-parent', 'no-scoped', 'subtree', 'deployment', 'port-deployment',
										'full-deployment', 'required', 'count', 'fault-count', 'tasks', 'deployment-records', 'ep-records',
										None]:
				raise Exception('Invalid value for rsp_include.')
			if opt not in ['count', 'no-scoped', 'required', None]:
				raise Exception('Invalid option for rsp_include.  Options are count, no-scoped, and required.')
		self.__subtree_include = subtree_include

	@property
	def parameters(self):
		parameters = {}
		if self.target is not None:
			parameters.update({'query-target': self.__target})
		if self.target_class is not None:
			parameters.update({'target-subtree-class': self.target_class})
		if self.filter is not None:
			parameters.update({'query-target-filter': self.filter})
		if self.include is not None:
			parameters.update({'rsp-prop-include': self.include})
		if self.subtree is not None:
			parameters.update({'rsp-subtree': self.subtree})
		if self.subtree_class is not None:
			parameters.update({'rsp-subtree-class': self.subtree_class})
		if self.subtree_filter is not None:
			parameters.update({'rsp-subtree-filter': self.subtree_filter})
		if self.subtree_include is not None:
			parameters.update({'rsp-subtree-include': self.subtree_include})
		if self.order is not None:
			parameters.update({'order-by': self.order})
		return parameters

	@parameters.setter
	def parameters(self, parameters):
		if parameters is None:
			parameters = {}
		if type(parameters) is not dict:
			raise Exception('Invalid parameters type. Must be a dictionary or None.')
		self.target = parameters['query-target'] if 'query-target' in parameters else None
		self.target_class = parameters['target-subtree-class'] if 'target-subtree-class' in parameters else None
		self.filter = parameters['query-target-filter'] if 'query-target-filter' in parameters else None
		self.include = parameters['rsp-prop-include'] if 'rsp-prop-include' in parameters else None
		self.subtree = parameters['rsp-subtree'] if 'rsp-subtree' in parameters else None
		self.subtree_class = parameters['rsp-subtree-class'] if 'rsp-subtree-class' in parameters else None
		self.subtree_filter = parameters['rsp-subtree-filter'] if 'rsp-subtree-filter' in parameters else None
		self.subtree_include = parameters['rsp-subtree-include'] if 'rsp-subtree-include' in parameters else None
		self.order = parameters['order-by'] if 'order-by' in parameters else None

	def run(self, path=None, show_output=False, show_parameters=False, show_count=False):
		if path is not None:
			self.path = path
		if path is not None and type(path) is not str:
			raise Exception('Invalid path.  Must be string.')
		if self.path is None:
			raise Exception('Path has not been set.')
		if show_parameters:
			print(json.dumps(self.parameters, indent=2))
		self.__data = data.Data(self.node.get(self.path, self.parameters))
		if show_count:
			print(self.output.count)
		if show_output:
			self.output.print()

	def reset(self):
		self.path = None
		self.parameters = None

	def save(self, filename):
		query = dict()
		query['node'] = self.node.address
		query['path'] = self.path
		query['parameters'] = self.parameters
		file = open(filename, 'w')
		file.write(json.dumps(query))
		file.close()

	def load(self, filename):
		file = open(filename)
		query = json.loads(file.read())
		file.close()
		self.node = node.Node(query['node'])
		self.path = query['path']
		self.parameters = query['parameters']

	def print(self, index=None, style='json'):
		self.__data.print(index, style)

