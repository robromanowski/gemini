# Finding Active Directory LDAP Connection Details using PowerShell

This guide provides PowerShell commands to help you discover or verify the necessary connection parameters required to configure an application (like a web service or script) to interact with your Active Directory environment via LDAP or LDAPS.

## Prerequisites

1.  **Active Directory PowerShell Module:** Ensure the module is installed and enabled on the machine where you run these commands. This is usually included in Remote Server Administration Tools (RSAT) for Windows clients or installed by default on Domain Controllers. You can typically install RSAT via "Windows Features" or using PowerShell: `Add-WindowsCapability -Online -Name Rsat.ActiveDirectory.DS-LDS.Tools~~~~0.0.1.0` (check exact name for your Windows version).
2.  **Domain-Joined Machine:** Run these commands from a computer that is joined to the Active Directory domain you are querying.
3.  **Permissions:** Log in as a domain user with at least permissions to read user and computer information from Active Directory. Standard domain user permissions are often sufficient for these read-only lookups.

---

## Finding Connection Details

Use the following commands to identify the specific parameters needed for your application's configuration.

### 1. Finding Domain Controllers (`AD_SERVER`)

These are the servers your application will connect to. While using the domain name itself (e.g., `yourdomain.com`) often works and allows DNS to handle discovery, you can find specific server hostnames.

```powershell
# Option A: Discover DCs in the current domain (recommended for finding options)
# Shows DCs serving LDAP requests
Get-ADDomainController -Discover -Service LDAP

# Option B: List details of all DCs in the current domain
Get-ADDomainController -Filter * | Select-Object Name, IPv4Address, Site, IsGlobalCatalog

# Option C: Discover DCs in a specific domain (if needed)
# Get-ADDomainController -Discover -DomainName "your.domain.com" -Service LDAP

# Option D: Use DNS SRV Record lookup (how clients typically find DCs)
$domainName = (Get-ADDomain).DNSRoot
Resolve-DnsName -Name "_ldap._tcp.dc._msdcs.$domainName" -Type SRV | Sort-Object Priority, Weight
```

* **Result:** These commands provide hostnames (e.g., `DC01.yourdomain.com`) that can be used for the `AD_SERVER` parameter in your application.

### 2. Verifying Port (`AD_PORT` / `AD_USE_SSL`)

* **Standard LDAP Port:** 389 (Unencrypted - **Not Recommended**)
* **Standard LDAPS Port:** 636 (LDAP over SSL/TLS - **Strongly Recommended**)

Use `Test-NetConnection` to verify if a Domain Controller is listening on the secure port (636).

```powershell
# Replace DC_HOSTNAME with a valid hostname found in Step 1
$dcHostname = "DC01.yourdomain.com" # <-- CHANGE THIS

Test-NetConnection -ComputerName $dcHostname -Port 636
```

* **Result:**
    * If `TcpTestSucceeded : True` for port 636, LDAPS is likely available. Configure your application with:
        * `AD_PORT='636'`
        * `AD_USE_SSL='true'`
    * If port 636 fails, you can check port 389 (`Test-NetConnection -ComputerName $dcHostname -Port 389`). If 389 succeeds, you *could* use:
        * `AD_PORT='389'`
        * `AD_USE_SSL='false'`
        * **Warning:** Using port 389 sends credentials and data unencrypted over the network. Avoid if possible.

### 3. Finding Service Account's Distinguished Name (`AD_BIND_USER`)

The application needs the full Distinguished Name (DN) of the dedicated service account it will use to authenticate (bind) to Active Directory.

```powershell
# Replace 'YourServiceAccountSamAccountName' with the actual sAMAccountName (login name)
# of the service account your application will use.
$samAccountName = "YourServiceAccountSamAccountName" # <-- CHANGE THIS

Get-ADUser -Identity $samAccountName | Select-Object DistinguishedName
```

* **Result:** This outputs the full DN required for the `AD_BIND_USER` parameter. Example: `CN=SvcMyApp,OU=Service Accounts,DC=yourdomain,DC=com`.

### 4. Finding the Search Base DN (`AD_SEARCH_BASE`)

This is the starting point in the Active Directory tree where your application will begin searching for objects (like users). Usually, this is the root DN of your domain.

```powershell
# Option A: Get the DN of the current domain
Get-ADDomain | Select-Object DistinguishedName

# Option B: Get the default naming context from RootDSE (Directory Service Agent Specific Entry)
(Get-ADRootDSE).defaultNamingContext
```

* **Result:** Both commands typically return the root DN of your domain (e.g., `DC=yourdomain,DC=com`). Use this value for the `AD_SEARCH_BASE` parameter. In specific cases, you might restrict the search to a particular Organizational Unit (OU), using that OU's DN instead (e.g., `OU=ManagedUsers,DC=yourdomain,DC=com`).

---

## Using the Information

Once you have gathered these details:

* **`AD_SERVER`**: Hostname of a DC (e.g., `dc01.yourdomain.com`) or the domain name (`yourdomain.com`).
* **`AD_PORT`**: `636` (recommended) or `389`.
* **`AD_USE_SSL`**: `true` (recommended) or `false`.
* **`AD_BIND_USER`**: The full DN of the service account (e.g., `CN=SvcMyApp,OU=Service Accounts,DC=yourdomain,DC=com`).
* **`AD_BIND_PASSWORD`**: The password for the service account. **Handle this securely!** Do not hardcode it. Use environment variables, secrets management tools, or secure configuration methods provided by your application framework.
* **`AD_SEARCH_BASE`**: The DN of the domain or specific OU (e.g., `DC=yourdomain,DC=com`).

Configure your application using these values, typically via environment variables or a configuration file, ensuring the service account password is managed securely.
