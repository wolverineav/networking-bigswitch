from neutronclient._i18n import _
from neutronclient.common import extension

class NetworkTemplate(extension.NeutronClientExtension):
	resource = 'networktemplate'
	resource_plural = '%ss' % resource
	object_path = '/%ss' % resource_plural
	resource_path = '/%s/%ss' % resource_plural
	versions = ['2.0']

class NetworkTemplateList(extension.ClientExtensionList, NetworkTemplate):
	"""List network templates"""
	shell_command = 'networktemplate-list'
	list_columns = ['id', 'template_name', 'body']






