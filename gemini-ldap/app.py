import os
from flask import Flask, render_template, request, flash
from ldap3 import Server, Connection, ALL, Tls, SAFE_SYNC
from ldap3.core.exceptions import LDAPBindError, LDAPException

# --- Configuration ---
# Load configuration securely from environment variables
AD_SERVER = os.environ.get('AD_SERVER')
AD_PORT = int(os.environ.get('AD_PORT', 636)) # Default to 636 if not set
AD_USE_SSL = os.environ.get('AD_USE_SSL', 'true').lower() == 'true'
AD_BIND_USER = os.environ.get('AD_BIND_USER')
AD_BIND_PASSWORD = os.environ.get('AD_BIND_PASSWORD')
AD_SEARCH_BASE = os.environ.get('AD_SEARCH_BASE')

# Basic validation of configuration
if not all([AD_SERVER, AD_BIND_USER, AD_BIND_PASSWORD, AD_SEARCH_BASE]):
    raise ValueError("Missing required AD configuration environment variables.")

# Configure TLS if using SSL (recommended)
tls_config = None
if AD_USE_SSL:
    # In a production environment, you might need to specify ca_certs_path
    # for validating the DC's certificate if it's not trusted by the system.
    # tls_config = Tls(validate=ssl.CERT_REQUIRED, ca_certs_path='/path/to/your/ca.crt')
    tls_config = Tls(validate=None) # Less secure: use for testing if cert validation fails
    print("Attempting LDAPS connection (SSL/TLS enabled)")
else:
    print("Warning: Attempting LDAP connection without SSL/TLS (unencrypted)")


app = Flask(__name__)
# Required for flashing messages
app.secret_key = os.urandom(24)

def get_ad_groups(username):
    """
    Connects to AD and retrieves direct group memberships for a given username.
    Returns a list of group names or raises an exception on error.
    """
    groups = []
    user_dn = None

    server = Server(AD_SERVER, port=AD_PORT, use_ssl=AD_USE_SSL, get_info=ALL, tls=tls_config)

    try:
        # Use SAFE_SYNC client strategy for simpler synchronous operations
        conn = Connection(server, user=AD_BIND_USER, password=AD_BIND_PASSWORD,
                          client_strategy=SAFE_SYNC, auto_bind=True)
        print(f"Successfully bound to AD as {AD_BIND_USER}")

        # 1. Search for the user by sAMAccountName to get their DN
        # Escape potentially problematic characters in username for LDAP filter
        search_filter = f'(&(objectClass=user)(sAMAccountName={ldap3.utils.conv.escape_filter_chars(username)}))'
        print(f"Searching for user with filter: {search_filter}")

        # Search specifically for the memberOf attribute
        conn.search(search_base=AD_SEARCH_BASE,
                    search_filter=search_filter,
                    attributes=['distinguishedName', 'memberOf', 'cn']) # 'cn' is useful for display name

        if conn.entries:
            user_entry = conn.entries[0]
            user_dn = user_entry.distinguishedName.value
            user_cn = user_entry.cn.value if 'cn' in user_entry else username # Fallback to username if CN not found
            print(f"Found user: {user_cn} (DN: {user_dn})")

            # 2. Retrieve the 'memberOf' attribute
            # memberOf contains the DNs of the groups the user is *directly* a member of
            group_dns = user_entry.memberOf.values
            print(f"Raw memberOf attribute: {group_dns}")

            if group_dns:
                 # Extract the Common Name (CN) from each group DN for readability
                for group_dn in group_dns:
                    # Simple parsing: assumes CN is the first part (e.g., "CN=GroupName,OU=Groups,...")
                    try:
                       cn_part = group_dn.split(',')[0]
                       if cn_part.upper().startswith('CN='):
                           groups.append(cn_part[3:])
                       else:
                           groups.append(group_dn) # Fallback if format is unexpected
                    except Exception:
                        groups.append(group_dn) # Fallback

                groups.sort() # Sort alphabetically
            else:
                 print(f"User {user_cn} has no direct group memberships listed in 'memberOf'.")


        else:
            print(f"User '{username}' not found in {AD_SEARCH_BASE}")
            raise ValueError(f"User '{username}' not found.")

        # Unbind the connection
        conn.unbind()
        print("Connection unbound.")
        return user_cn, groups # Return username and list of groups

    except LDAPBindError as e:
        print(f"LDAP Bind Error: {e}")
        flash(f"Error connecting or binding to Active Directory. Check service account credentials and DC availability. Details: {e}", "error")
        raise # Re-raise to be caught by the route
    except LDAPException as e:
        print(f"LDAP Error: {e}")
        flash(f"An LDAP error occurred during the search. Details: {e}", "error")
        raise # Re-raise
    except Exception as e:
        # Catch other potential errors (network, config)
        print(f"An unexpected error occurred: {e}")
        flash(f"An unexpected error occurred: {e}", "error")
        raise # Re-raise


@app.route('/', methods=['GET', 'POST'])
def index():
    groups = None
    error_message = None
    searched_user = None # Keep track of the user that was searched for

    if request.method == 'POST':
        username = request.form.get('username')
        searched_user = username # Store for display even if lookup fails
        if username:
            try:
                print(f"--- Initiating search for username: {username} ---")
                display_name, groups = get_ad_groups(username)
                searched_user = f"{display_name} ({username})" # Update with display name if found
                if not groups:
                     flash(f"User '{searched_user}' found, but is not a direct member of any groups.", "warning")
                print(f"--- Search complete for {username}. Groups found: {len(groups) if groups else 0} ---")
            except ValueError as e: # Catch specific "user not found" error
                error_message = str(e)
                flash(error_message, "error")
                print(f"--- Search failed for {username}: {error_message} ---")
            except Exception as e: # Catch other errors raised from get_ad_groups
                # Flash message is already set within get_ad_groups for LDAP errors
                 if not any(category == 'error' for category, _ in app.jinja_env.globals['get_flashed_messages'](with_categories=True)):
                    flash(f"An unexpected error occurred processing the request for '{username}'. Check logs.", "error")
                print(f"--- Search failed for {username} due to caught exception: {e} ---")
        else:
            error_message = "Please enter a username."
            flash(error_message, "warning")

    # Render the template, passing the results (or None)
    return render_template('index.html', groups=groups, error_message=error_message, searched_user=searched_user, username_value=request.form.get('username', ''))


if __name__ == '__main__':
    # Run in debug mode for development (auto-reloads, provides debugger)
    # Make sure to turn debug mode OFF for production deployment!
    app.run(debug=True, host='0.0.0.0', port=5000) # Listen on all interfaces
