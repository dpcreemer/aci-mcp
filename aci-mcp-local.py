#!/usr/bin/env python
"""
This is a library of tools to facilitate interaction with an ACI Fabric.  
Currently Query and creation tools are included.  Deletions are not currently supported by this tool set.
Object data should always be queried from the fabric.  No guess or estimate of object information should be made.
"""
import json, os
from fabric import Fabric
from fastmcp import FastMCP

mcp = FastMCP("ACI")
_FABRIC = None

def _get_settings() -> dict:
  settings = {
    "mcp_transport": "stdio",
    "mcp_host": "0.0.0.0",
    "mcp_port": "8000",
    "apic_address": "",
    "username": "",
    "password": ""
  }

  for key in settings:
    if key.upper() in os.environ:
      settings[key] = os.environ[key.upper()]

  if not os.path.exists("settings.json"):
    return settings
  
  with open("settings.json") as f:
    file_settings = json.loads(f.read())
  
  for key in settings:
    if key in file_settings:
      settings[key] = file_settings[key]
  
  return settings

def get_fabric() -> Fabric:
  global _FABRIC
  if isinstance(_FABRIC, Fabric): 
    return _FABRIC
  
  settings = _get_settings()
  
  fab = Fabric(settings["apic_address"], settings["username"], settings["password"])
  fab.login()
  _FABRIC = fab
  return fab

@mcp.tool
def list_tenants() -> list[dict]:
  """
  Get a list of tenants
  returns data on the tenants: 
  name, alias, description, and dn (distinguished name)
  """
  fab = get_fabric()
  data = fab.query("fvTenant").run().json
  rv = []
  for tn in data:
    rv.append(
      {
        "name": tn["fvTenant"]["attributes"]["name"], 
        "alias": tn["fvTenant"]["attributes"]["nameAlias"], 
        "description": tn["fvTenant"]["attributes"]["descr"],
        "dn": tn["fvTenant"]["attributes"]["dn"]
      }
    )
  return rv

@mcp.tool
def create_a_tenant(name: str, alias: str = "", description: str = "") -> str:
  """
  Create a tenant in the fabric
  returns as status that indicates if the post was successful
  """
  fab = get_fabric()
  payload = {
    "fvTenant": {
      "attributes": {
        "dn": f"uni/tn-{name}",
        "name": name,
        "nameAlias": alias,
        "descr": description,
        "annotation": "orchestrator:mcp"
      }
    }
  }
  rv = fab.post(payload)
  if rv != 200:
    return fab.apic.response.text
  return "success"

@mcp.tool
def modify_tenant(tenant_name: str, 
              alias: str | None = None,
              description: str | None = None) -> str:
  """
  Modify an existing tenant identified by name
  name must be provided by user, no assumptions.
  args:
    tenant_name - the name of tenant to modify
    alias - the Alias for the tenant
    description - a description for the Tenant
  """
  fab = get_fabric()
  payload = {
    "fvTenant": {
      "attributes": {
        "dn": f"uni/tn-{tenant_name}"
      }
    }
  }
  if alias is not None:
    payload["fvTenant"]["attributes"]["nameAlias"] = alias
  if description is not None:
    payload["fvTenant"]["attributes"]["descr"] = description
  rv = fab.post(payload)
  if not rv == 200:
    return fab.apic.response.text
  return "success"

@mcp.tool
def list_vrfs(tenant_name: str) -> list[dict]:
  """
  Get a list of VRF in a tenant
  args:
    tenant_name: the name of the tenant to search
  returns data on the VRF
    name, alias, description, dn
  """
  fab = get_fabric()
  dn = f"uni/tn-{tenant_name}"
  data = fab.query(dn, target="children", target_class="fvCtx").run().json
  rv = []
  for vrf in data:
    rv.append(
      {
        "name": vrf["fvCtx"]["attributes"]["name"],
        "alias": vrf["fvCtx"]["attributes"]["nameAlias"],
        "description": vrf["fvCtx"]["attributes"]["descr"],
        "dn": vrf["fvCtx"]["attributes"]["dn"]
      }
    )
  return rv

@mcp.tool
def create_a_vrf(tenant_name: str,
                 name: str,
                 alias: str = "",
                 description: str = "") -> str:
  """
  Create a new VRF within the indicated tenant.
  args:
    tenant_name - the name of the tenant where the VRF should be created
    name - a name for the new VRF
    alias - (optional) an alias for the new VRF
    description - (optional) a description for the new VRF
  """
  fab = get_fabric()
  payload = {
    "fvCtx": {
      "attributes": {
        "dn": f"uni/tn-{tenant_name}/ctx-{name}",
        "name": name,
        "nameAlias": alias,
        "descr": description,
        "annotation": "orchestrator:mcp"
      }
    }
  }
  rv = fab.post(payload)
  if not rv == 200:
    return fab.apic.response.text
  return "success"

@mcp.tool
def modify_vrf(tenant_name: str, 
              vrf_name: str,
              alias: str = "",
              description: str = "") -> str:
  """
  Modify an existing VRF identified by tenant and VRF name 
  tenant and name must be provided by user, no assumptions.
  args:
    tenant_name - the name of tenant where the VRF exists
    vrf_name - the name of the VRF to be modified
    alias - the Alias for the VRF
    description - a description for the VRF
  """
  fab = get_fabric()
  payload = {
    "fvCtx": {
      "attributes": {
        "dn": f"uni/tn-{tenant_name}/ctx-{vrf_name}"
      }
    }
  }
  if alias:
    payload["fvCtx"]["attributes"]["nameAlias"] = alias
  if description:
    payload["fvCtx"]["attributes"]["descr"] = description
  rv = fab.post(payload)
  if not rv == 200:
    return fab.apic.response.text
  return "success"

@mcp.tool
def list_bds(tenant_name: str) -> list[dict]:
  """
  Get a list of Bridge Domains (BDs) in a tenant
  args:
    tenant_name: the name of the tenant to search
  returns data on the BDs
    name, alias, description, dn
  """
  fab = get_fabric()
  dn = f"uni/tn-{tenant_name}"
  data = fab.query(dn, target="children", target_class="fvBD").run().json
  rv = []
  for bd in data:
    rv.append(
      {
        "name": bd["fvBD"]["attributes"]["name"],
        "alias": bd["fvBD"]["attributes"]["nameAlias"],
        "description": bd["fvBD"]["attributes"]["descr"],
        "dn": bd["fvBD"]["attributes"]["dn"]
      }
    )
  return rv

@mcp.tool
def get_bd_info(tenant_name: str, bd_name: str) -> dict:
  """
  Get information about a specific bridge domain
  args:
    tenant_name: the name of the tenant where the BD is found
    bd_name: the name of the BD
  returns detailed data on the BD:
    name, alias, description, vrf, subnets, dn, etc.
  """
  fab = get_fabric()
  dn = f"uni/tn-{tenant_name}/BD-{bd_name}"
  data = fab.query(dn, subtree="full", include="config").run().json
  if len(data) == 0: 
    return {}
  data = data[0]
  rv = {
    "name": data["fvBD"]["attributes"]["name"],
    "alias": data["fvBD"]["attributes"]["nameAlias"],
    "description": data["fvBD"]["attributes"]["descr"],
    "dn": data["fvBD"]["attributes"]["dn"],
    "vrf": [c["fvRsCtx"]["attributes"]["tnFvCtxName"] for c in data['fvBD']['children'] if "fvRsCtx" in c][0],
    "subnets": [c["fvSubnet"]["attributes"]["ip"] for c in data['fvBD']['children'] if "fvSubnet" in c]
  }
  return rv

@mcp.tool
def modify_bd(tenant_name: str, 
              bd_name: str,
              vrf: str = "",
              alias: str = "",
              description: str = "") -> str:
  """
  Modify an existing Bridge Domain (BD) identified by tenant and bd
  tenant and name must be provided by user, no assumptions.
  args:
    tenant_name - the name of tenant where the BD exists
    bd_name - the name of the BD to be modified
    vrf - the VRF where the BD should be located
    alias - the Alias for the BD
    description - a description for the BD
  """
  fab = get_fabric()
  payload = {
    "fvBD": {
      "attributes": {
        "dn": f"uni/tn-{tenant_name}/BD-{bd_name}"
      }
    }
  }
  if vrf:
    payload["fvBD"]["children"] = [
      {
        "fvRsCtx": {
          "attributes": {
            "tnFvCtxName": vrf
          }
        }
      }
    ]
  if alias:
    payload["fvBD"]["attributes"]["nameAlias"] = alias
  if description:
    payload["fvBD"]["attributes"]["descr"] = description
  rv = fab.post(payload)
  if not rv == 200:
    return fab.apic.response.text
  return "success"

@mcp.tool
def create_a_bd(tenant_name: str,
                name: str,
                vrf: str,
                alias: str = "",
                description: str = "",
              ) -> str:
  """
  Create a new Bridge Domian (BD) within the indicated tenant.
  Tenant, name, and vrf must be provided by user, no assumptions.
  args:
    tenant_name - the name of the tenant where the BD should be created
    name - a name for the new BD
    vrf - the VRF that the BD should be associated with
    alias - (optional) an alias for the new BD
    description - (optional) a description for the new BD
  """
  fab = get_fabric()
  payload = {
    "fvBD": {
      "attributes": {
        "dn": f"uni/tn-{tenant_name}/BD-{name}",
        "name": name,
        "nameAlias": alias,
        "descr": description
      },
      "children":[
        {
          "fvRsCtx": {
            "attributes": {
              "tnFvCtxName": vrf
            }
          }
        }
      ]
    }
  }
  rv = fab.post(payload)
  if not rv == 200:
    return fab.apic.response.text
  return "success"
  
@mcp.tool
def list_aps(tenant_name: str) -> list[dict]:
  """
  Get a list of Application Profiles (APs) in a tenant
  args:
    tenant_name: the name of the tenant to search
  returns data on APs:
    name, alias, description, dn (distinguished name)
  """ 
  fab = get_fabric()
  dn = f"uni/tn-{tenant_name}"
  data = fab.query(dn, target="children", target_class="fvAp").run().json
  rv = []
  for ap in data:
    rv.append(
      {
        "name": ap["fvAp"]["attributes"]["name"],
        "alias": ap["fvAp"]["attributes"]["nameAlias"],
        "description": ap["fvAp"]["attributes"]["descr"],
        "dn": ap["fvAp"]["attributes"]["dn"]
      } 
    )
  return rv

@mcp.tool
def create_an_ap(tenant_name: str,
                 name: str,
                 alias: str = "",
                 description: str = "") -> str:
  """
  Create a new Application Profile within the indicated tenant.
  args:
    tenant_name - the name of the tenant where AP should be created
    name - a name for the new AP
    alias - (optional) an alias for the new AP
    description - (optional) a description for the new AP
  """
  fab = get_fabric()
  payload = {
    "fvAp": {
      "attributes": {
        "dn": f"uni/tn-{tenant_name}/ap-{name}",
        "name": name,
        "nameAlias": alias,
        "descr": description
      }
    }
  }
  rv = fab.post(payload)
  if not rv == 200:
    return fab.apic.response.text
  return "success"


@mcp.tool
def list_epgs(tenant_name: str, ap_name: str | None = None) -> list[dict]:
  """
  Get a list of Endpoint Groups (EPGs)
  args:
    tenant_name - the tenant containing the EPGs
    ap_name - (optional) the Application Profile containing the EPGs
  returns data on EPGs
    name, alias, description, pctag (VXLAN ID used for security tagging), dn
  """
  fab = get_fabric()
  dn = f"uni/tn-{tenant_name}"
  if ap_name:
    dn += f"/ap-{ap_name}"

  data = fab.query(dn, target="subtree", target_class="fvAEPg").run().json
  rv = []
  for epg in data:
    rv.append(
      {
        "name": epg["fvAEPg"]["attributes"]["name"],
        "alias": epg["fvAEPg"]["attributes"]["nameAlias"],
        "description": epg["fvAEPg"]["attributes"]["descr"],
        "pcTag": epg["fvAEPg"]["attributes"]["pcTag"],
        "dn": epg["fvAEPg"]["attributes"]["dn"]
      }
    )
  return rv

@mcp.tool
def list_nodes() -> list[dict]:
  """
  Get a list of fabric nodes (Controllers and switches)
  returns data on the nodes:
  id, name, role, address, model, serial number, and dn
  """
  fab = get_fabric()
  data = fab.query("fabricNode").run().json
  rv = [{
    "id": node["fabricNode"]["attributes"]["id"],
    "name": node["fabricNode"]["attributes"]["name"],
    "role": node["fabricNode"]["attributes"]["role"],
    "address": node["fabricNode"]["attributes"]["address"],
    "model": node["fabricNode"]["attributes"]["model"],
    "serial_number": node["fabricNode"]["attributes"]["serial"],
    "dn": node["fabricNode"]["attributes"]["dn"]}
    for node in data
  ]
  return rv

if __name__ == "__main__":
  # default to HTTP for container use; you can override to "stdio" for local
  settings = _get_settings()
  transport = settings["mcp_transport"]

  if transport == "http":
    print("transport is http")
    port = settings["mcp_port"]
    host = settings["mcp_host"]
    print(f"listening at {host}:{port}")
    mcp.run(transport=transport, host=host, port=port)  # HTTP MCP at /mcp
  else:
    # classic local/stdio mode for ollmcp etc.
    print("transport is not http")
    mcp.run()
