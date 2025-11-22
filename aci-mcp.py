#!/usr/bin/env python
import json
from fabric import Fabric
from fastmcp import FastMCP

mcp = FastMCP("ACI")
_FABRIC = None

def get_fabric() -> Fabric:
  global _FABRIC
  if isinstance(_FABRIC, Fabric): 
    return _FABRIC

  with open("settings.json") as f:
    settings = json.loads(f.read())
  
  fab = Fabric(settings["address"], settings["username"], settings["password"])
  fab.login()
  _FABRIC
  return fab

@mcp.tool
def list_tenants() -> list[dict]:
  """
  Get a list of tenants
  returns data on the tenants: 
  name, alias, description, and dn (distinguished name)
  """
  fab = get_fabric()
  data = fab.qr("fvTenant").data.json
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
        "descr": description
      }
    }
  }
  rv = fab.post(payload)
  if rv != 200:
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
  data = fab.qr(dn, target="children", target_class="fvCtx").data.json
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
        "descr": description
      }
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
  data = fab.qr(dn, target="children", target_class="fvAp").data.json
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

  data = fab.qr(dn, target="subtree", target_class="fvAEPg").data.json
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
  data = fab.qr("fabricNode").data.json
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
  mcp.run()
