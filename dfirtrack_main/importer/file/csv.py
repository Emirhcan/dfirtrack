import csv
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
import dfirtrack.config as dfirtrack_config
from dfirtrack.config import SYSTEMTAG_HEADLINE as systemtag_headline
from dfirtrack.config import SYSTEMTAG_SUBHEADLINE as systemtag_subheadline
from dfirtrack.config import TAGLIST
from dfirtrack.config import TAGPREFIX
from dfirtrack_main.forms import SystemImporterFileCsv, SystemIpFileImport, SystemTagFileImport
from dfirtrack_main.logger.default_logger import critical_logger, debug_logger, error_logger, warning_logger
from dfirtrack_main.models import Analysisstatus, Dnsname, Domain, Headline, Ip, Location, Os, Reason, Reportitem, Serviceprovider, System, Systemstatus, Systemtype, Tag, Tagcolor
import ipaddress
from io import TextIOWrapper
# TODO: remove not needed imports

def check_and_create_ip(column_ip, request, row_counter):

    # check ip column for ip
    try:
        ipaddress.ip_address(column_ip)
    except ValueError:
        messages.error(request, "Value in row " + str(row_counter) + " was not a valid IP address.")
        # call logger
        warning_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV_IP_COLUMN " + "row_" + str(row_counter) + ":invalid_ip")
        return None

    # create ip
    ip, created = Ip.objects.get_or_create(ip_ip=column_ip)
    if created == True:
        ip.logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV_IP_CREATED")

    return ip

def optional_system_attributes(system):

    # add optional attributes if applicable
    if dfirtrack_config.CSV_CHOICE_ANALYSISSTATUS:
        system.analysisstatus = Analysisstatus.objects.get(analysisstatus_name = dfirtrack_config.CSV_DEFAULT_ANALYSISSTATUS)
    if dfirtrack_config.CSV_CHOICE_REASON:
        system.reason = Reason.objects.get(reason_id = dfirtrack_config.CSV_DEFAULT_REASON)
    if dfirtrack_config.CSV_CHOICE_DOMAIN:
        system.domain = Domain.objects.get(domain_id = dfirtrack_config.CSV_DEFAULT_DOMAIN)
    if dfirtrack_config.CSV_CHOICE_DNSNAME:
        system.dnsname = Dnsname.objects.get(dnsname_id = dfirtrack_config.CSV_DEFAULT_DNSNAME)
    if dfirtrack_config.CSV_CHOICE_SYSTEMTYPE:
        system.systemtype = Systemtype.objects.get(systemtype_id = dfirtrack_config.CSV_DEFAULT_SYSTEMTYPE)
    if dfirtrack_config.CSV_CHOICE_OS:
        system.os = Os.objects.get(os_id = dfirtrack_config.CSV_DEFAULT_OS)
    if dfirtrack_config.CSV_CHOICE_LOCATION:
        system.location = Location.objects.get(location_id = dfirtrack_config.CSV_DEFAULT_LOCATION)
    if dfirtrack_config.CSV_CHOICE_SERVICEPROVIDER:
        system.serviceprovider = Serviceprovider.objects.get(serviceprovider_id = dfirtrack_config.CSV_DEFAULT_SERVICEPROVIDER)

    return system

@login_required(login_url="/login")
def system(request):

    # form was valid to post
    if request.method == "POST":

        # call logger
        debug_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV_BEGAN")

        """ check variables of dfirtrack.config """

        # reset stop condition
        stop_system_importer_file_csv = False

        # check CSV_HEADLINE for bool
        if not isinstance(dfirtrack_config.CSV_HEADLINE, bool):
            messages.error(request, "Deformed `CSV_HEADLINE` Check `dfirtrack.config`!")
            # call logger
            warning_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV variable CSV_HEADLINE deformed")
            stop_system_importer_file_csv = True

        # check CSV_SKIP_EXISTING_SYSTEM for bool
        if not isinstance(dfirtrack_config.CSV_SKIP_EXISTING_SYSTEM, bool):
            messages.error(request, "Deformed `CSV_SKIP_EXISTING_SYSTEM` Check `dfirtrack.config`!")
            # call logger
            warning_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV variable CSV_SKIP_EXISTING_SYSTEM deformed")
            stop_system_importer_file_csv = True

        # check CSV_COLUMN_SYSTEM for int
        if not isinstance(dfirtrack_config.CSV_COLUMN_SYSTEM, int):
            messages.error(request, "Deformed `CSV_COLUMN_SYSTEM` Check `dfirtrack.config`!")
            # call logger
            warning_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV variable CSV_COLUMN_SYSTEM deformed")
            stop_system_importer_file_csv = True

        # check CSV_DEFAULT_SYSTEMSTATUS for existence
        try:
            Systemstatus.objects.get(systemstatus_name = dfirtrack_config.CSV_DEFAULT_SYSTEMSTATUS)
        except Systemstatus.DoesNotExist:
            messages.warning(request, "Systemstatus with configured name does not exist. Check `dfirtrack.config` or create systemstatus!")
            # call logger
            warning_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV systemstatus for variable CSV_DEFAULT_SYSTEMSTATUS does not exist")
            stop_system_importer_file_csv = True

        # check CSV_CHOICE_ANALYSISSTATUS for bool
        if not isinstance(dfirtrack_config.CSV_CHOICE_ANALYSISSTATUS, bool):
            messages.error(request, "Deformed `CSV_CHOICE_ANALYSISSTATUS` Check `dfirtrack.config`!")
            # call logger
            warning_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV variable CSV_CHOICE_ANALYSISSTATUS deformed")
            stop_system_importer_file_csv = True

        # check CSV_DEFAULT_ANALYSISSTATUS (check only if CSV_CHOICE_ANALYSISSTATUS is True) for existence
        if dfirtrack_config.CSV_CHOICE_ANALYSISSTATUS:
            try:
                Analysisstatus.objects.get(analysisstatus_name = dfirtrack_config.CSV_DEFAULT_ANALYSISSTATUS)
            except Analysisstatus.DoesNotExist:
                messages.warning(request, "Analysisstatus with configured name does not exist. Check `dfirtrack.config` or create analysisstatus!")
                # call logger
                warning_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV analysisstatus for variable CSV_DEFAULT_ANALYSISSTATUS does not exist")
                stop_system_importer_file_csv = True

        # check CSV_CHOICE_REASON for bool
        if not isinstance(dfirtrack_config.CSV_CHOICE_REASON, bool):
            messages.error(request, "Deformed `CSV_CHOICE_REASON` Check `dfirtrack.config`!")
            # call logger
            warning_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV variable CSV_CHOICE_REASON deformed")
            stop_system_importer_file_csv = True

        # check CSV_DEFAULT_REASON (check only if CSV_CHOICE_REASON is True) for existence
        if dfirtrack_config.CSV_CHOICE_REASON:
            try:
                Reason.objects.get(reason_id = dfirtrack_config.CSV_DEFAULT_REASON)
            except Reason.DoesNotExist:
                messages.warning(request, "Reason with configured ID does not exist. Check `dfirtrack.config` or create reason!")
                # call logger
                warning_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV reason for variable CSV_DEFAULT_REASON does not exist")
                stop_system_importer_file_csv = True
            except ValueError:
                messages.error(request, "Deformed `CSV_DEFAULT_REASON` Check `dfirtrack.config`!")
                # call logger
                warning_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV variable CSV_DEFAULT_REASON deformed")
                stop_system_importer_file_csv = True

        # check CSV_CHOICE_IP for bool
        if not isinstance(dfirtrack_config.CSV_CHOICE_IP, bool):
            messages.error(request, "Deformed `CSV_CHOICE_IP` Check `dfirtrack.config`!")
            # call logger
            warning_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV variable CSV_CHOICE_IP deformed")
            stop_system_importer_file_csv = True

        # check CSV_COLUMN_IP for int
        if not isinstance(dfirtrack_config.CSV_COLUMN_IP, int):
            messages.error(request, "Deformed `CSV_COLUMN_IP` Check `dfirtrack.config`!")
            # call logger
            warning_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV variable CSV_COLUMN_IP deformed")
            stop_system_importer_file_csv = True

        # check CSV_CHOICE_DOMAIN for bool
        if not isinstance(dfirtrack_config.CSV_CHOICE_DOMAIN, bool):
            messages.error(request, "Deformed `CSV_CHOICE_DOMAIN` Check `dfirtrack.config`!")
            # call logger
            warning_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV variable CSV_CHOICE_DOMAIN deformed")
            stop_system_importer_file_csv = True

        # check CSV_DEFAULT_DOMAIN (check only if CSV_CHOICE_DOMAIN is True) for existence
        if dfirtrack_config.CSV_CHOICE_DOMAIN:
            try:
                Domain.objects.get(domain_id = dfirtrack_config.CSV_DEFAULT_DOMAIN)
            except Domain.DoesNotExist:
                messages.warning(request, "Domain with configured ID does not exist. Check `dfirtrack.config` or create domain!")
                # call logger
                warning_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV domain for variable CSV_DEFAULT_DOMAIN does not exist")
                stop_system_importer_file_csv = True
            except ValueError:
                messages.error(request, "Deformed `CSV_DEFAULT_DOMAIN` Check `dfirtrack.config`!")
                # call logger
                warning_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV variable CSV_DEFAULT_DOMAIN deformed")
                stop_system_importer_file_csv = True

        # check CSV_CHOICE_DNSNAME for bool
        if not isinstance(dfirtrack_config.CSV_CHOICE_DNSNAME, bool):
            messages.error(request, "Deformed `CSV_CHOICE_DNSNAME` Check `dfirtrack.config`!")
            # call logger
            warning_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV variable CSV_CHOICE_DNSNAME deformed")
            stop_system_importer_file_csv = True

        # check CSV_DEFAULT_DNSNAME (check only if CSV_CHOICE_DNSNAME is True) for existence
        if dfirtrack_config.CSV_CHOICE_DNSNAME:
            try:
                Dnsname.objects.get(dnsname_id = dfirtrack_config.CSV_DEFAULT_DNSNAME)
            except Dnsname.DoesNotExist:
                messages.warning(request, "Dnsname with configured ID does not exist. Check `dfirtrack.config` or create dnsname!")
                # call logger
                warning_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV dnsname for variable CSV_DEFAULT_DNSNAME does not exist")
                stop_system_importer_file_csv = True
            except ValueError:
                messages.error(request, "Deformed `CSV_DEFAULT_DNSNAME` Check `dfirtrack.config`!")
                # call logger
                warning_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV variable CSV_DEFAULT_DNSNAME deformed")
                stop_system_importer_file_csv = True

        # check CSV_CHOICE_SYSTEMTYPE for bool
        if not isinstance(dfirtrack_config.CSV_CHOICE_SYSTEMTYPE, bool):
            messages.error(request, "Deformed `CSV_CHOICE_SYSTEMTYPE` Check `dfirtrack.config`!")
            # call logger
            warning_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV variable CSV_CHOICE_SYSTEMTYPE deformed")
            stop_system_importer_file_csv = True

        # check CSV_DEFAULT_SYSTEMTYPE (check only if CSV_CHOICE_SYSTEMTYPE is True) for existence
        if dfirtrack_config.CSV_CHOICE_SYSTEMTYPE:
            try:
                Systemtype.objects.get(systemtype_id = dfirtrack_config.CSV_DEFAULT_SYSTEMTYPE)
            except Systemtype.DoesNotExist:
                messages.warning(request, "Systemtype with configured ID does not exist. Check `dfirtrack.config` or create systemtype!")
                # call logger
                warning_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV systemtype for variable CSV_DEFAULT_SYSTEMTYPE does not exist")
                stop_system_importer_file_csv = True
            except ValueError:
                messages.error(request, "Deformed `CSV_DEFAULT_SYSTEMTYPE` Check `dfirtrack.config`!")
                # call logger
                warning_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV variable CSV_DEFAULT_SYSTEMTYPE deformed")
                stop_system_importer_file_csv = True

        # check CSV_CHOICE_OS for bool
        if not isinstance(dfirtrack_config.CSV_CHOICE_OS, bool):
            messages.error(request, "Deformed `CSV_CHOICE_OS` Check `dfirtrack.config`!")
            # call logger
            warning_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV variable CSV_CHOICE_OS deformed")
            stop_system_importer_file_csv = True

        # check CSV_DEFAULT_OS (check only if CSV_CHOICE_OS is True) for existence
        if dfirtrack_config.CSV_CHOICE_OS:
            try:
                Os.objects.get(os_id = dfirtrack_config.CSV_DEFAULT_OS)
            except Os.DoesNotExist:
                messages.warning(request, "OS with configured ID does not exist. Check `dfirtrack.config` or create OS!")
                # call logger
                warning_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV OS for variable CSV_DEFAULT_OS does not exist")
                stop_system_importer_file_csv = True
            except ValueError:
                messages.error(request, "Deformed `CSV_DEFAULT_OS` Check `dfirtrack.config`!")
                # call logger
                warning_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV variable CSV_DEFAULT_OS deformed")
                stop_system_importer_file_csv = True

        # check CSV_CHOICE_LOCATION for bool
        if not isinstance(dfirtrack_config.CSV_CHOICE_LOCATION, bool):
            messages.error(request, "Deformed `CSV_CHOICE_LOCATION` Check `dfirtrack.config`!")
            # call logger
            warning_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV variable CSV_CHOICE_LOCATION deformed")
            stop_system_importer_file_csv = True

        # check CSV_DEFAULT_LOCATION (check only if CSV_CHOICE_LOCATION is True) for existence
        if dfirtrack_config.CSV_CHOICE_LOCATION:
            try:
                Location.objects.get(location_id = dfirtrack_config.CSV_DEFAULT_LOCATION)
            except Location.DoesNotExist:
                messages.warning(request, "Location with configured ID does not exist. Check `dfirtrack.config` or create location!")
                # call logger
                warning_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV location for variable CSV_DEFAULT_LOCATION does not exist")
                stop_system_importer_file_csv = True
            except ValueError:
                messages.error(request, "Deformed `CSV_DEFAULT_LOCATION` Check `dfirtrack.config`!")
                # call logger
                warning_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV variable CSV_DEFAULT_LOCATION deformed")
                stop_system_importer_file_csv = True

        # check CSV_CHOICE_SERVICEPROVIDER for bool
        if not isinstance(dfirtrack_config.CSV_CHOICE_SERVICEPROVIDER, bool):
            messages.error(request, "Deformed `CSV_CHOICE_SERVICEPROVIDER` Check `dfirtrack.config`!")
            # call logger
            warning_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV variable CSV_CHOICE_SERVICEPROVIDER deformed")
            stop_system_importer_file_csv = True

        # check CSV_DEFAULT_SERVICEPROVIDER (check only if CSV_CHOICE_SERVICEPROVIDER is True) for existence
        if dfirtrack_config.CSV_CHOICE_SERVICEPROVIDER:
            try:
                Serviceprovider.objects.get(serviceprovider_id = dfirtrack_config.CSV_DEFAULT_SERVICEPROVIDER)
            except Serviceprovider.DoesNotExist:
                messages.warning(request, "Serviceprovider with configured ID does not exist. Check `dfirtrack.config` or create serviceprovider!")
                # call logger
                warning_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV serviceprovider for variable CSV_DEFAULT_SERVICEPROVIDER does not exist")
                stop_system_importer_file_csv = True
            except ValueError:
                messages.error(request, "Deformed `CSV_DEFAULT_SERVICEPROVIDER` Check `dfirtrack.config`!")
                # call logger
                warning_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV variable CSV_DEFAULT_SERVICEPROVIDER deformed")
                stop_system_importer_file_csv = True

        # leave system_importer_file_csv if variables caused errors
        if stop_system_importer_file_csv:

            messages.warning(request, "Nothing was changed.")
            # call logger
            warning_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV_END_WITH_ERRORS")
            return redirect(reverse('system_list'))

        # get text out of file (variable results from request object via file upload field)
        systemcsv = TextIOWrapper(request.FILES['systemcsv'].file, encoding=request.encoding)

        # read rows out of csv
        rows = csv.reader(systemcsv, quotechar="'")

        """ prepare and start loop """

        # set row_counter (needed for logger)
        row_counter = 1

        # set systems_created_counter (needed for messages)
        systems_created_counter = 0

        # set systems_updated_counter (needed for messages)
        systems_updated_counter = 0

        # set systems_skipped_counter (needed for messages)
        systems_skipped_counter = 0

        # iterate over rows
        for row in rows:

            # skip first row in case of headline
            if row_counter == 1 and dfirtrack_config.CSV_HEADLINE is True:
                # autoincrement row counter
                row_counter += 1
                # leave loop for headline row
                continue

            # TODO: check rows
            # TODO: check columns for values

            # get system name
            system_name = row[dfirtrack_config.CSV_COLUMN_SYSTEM]

            # get all systems with this system_name
            systemquery = System.objects.filter(system_name=system_name)

            """ check how many systems were returned """

            # if there is only one system
            if len(systemquery) == 1:

                # skip if system already exists (depending on CSV_SKIP_EXISTING_SYSTEM)
                if dfirtrack_config.CSV_SKIP_EXISTING_SYSTEM:

                    # autoincrement counter
                    systems_skipped_counter += 1
                    # leave loop
                    continue

                # modify existing system (depending on CSV_SKIP_EXISTING_SYSTEM)
                elif not dfirtrack_config.CSV_SKIP_EXISTING_SYSTEM:

                    # get system object
                    system = System.objects.get(system_name=system_name)

                    # change mandatory attribute
                    system.systemstatus = Systemstatus.objects.get(systemstatus_name = dfirtrack_config.CSV_DEFAULT_SYSTEMSTATUS)

                    # change optional attributes if applicable
                    system = optional_system_attributes(system)

                    # change mandatory meta attributes
                    system.system_modify_time = timezone.now()
                    system.system_modified_by_user_id = request.user

                    # save object
                    system.save()

                    # get ip address
                    if dfirtrack_config.CSV_CHOICE_IP:
                        column_ip = row[dfirtrack_config.CSV_COLUMN_IP]
                        ip_address = check_and_create_ip(column_ip, request, row_counter)

                    # TODO: maybe remove previously linked IPs because of many to many relation
                    # TODO: test showed that ips will be added to previous existing --> maybe choice overwrite or add?
                    # save ip for system (if valid value was provided)
                    if dfirtrack_config.CSV_CHOICE_IP:
                        if ip_address:
                            system.ip.add(ip_address)

                    # autoincrement systems_updated_counter
                    systems_updated_counter += 1

                    # call logger
                    system.logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV_SYSTEM_MODIFIED")

            # if there is more than one system
            elif len(systemquery) > 1:
                pass
                # TODO: add routine for duplicate systems (add least some kind of message / log)

            # if there is no system
            else:
                # create new system object
                system = System()
                system.system_name = system_name

                # add mandatory attributes
                system.systemstatus = Systemstatus.objects.get(systemstatus_name = dfirtrack_config.CSV_DEFAULT_SYSTEMSTATUS)

                # add optional attributes if applicable
                system = optional_system_attributes(system)

                # add mandatory meta attributes
                system.system_modify_time = timezone.now()
                system.system_created_by_user_id = request.user
                system.system_modified_by_user_id = request.user

                # save object
                system.save()

                # get ip address
                if dfirtrack_config.CSV_CHOICE_IP:
                    column_ip = row[dfirtrack_config.CSV_COLUMN_IP]
                    ip_address = check_and_create_ip(column_ip, request, row_counter)

                # save ip for system (if valid value was provided)
                if dfirtrack_config.CSV_CHOICE_IP:
                    if ip_address:
                        system.ip.add(ip_address)

                # autoincrement systems_created_counter
                systems_created_counter += 1

                # call logger
                system.logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV_SYSTEM_CREATED")

            # autoincrement row counter
            row_counter += 1

        # call final messages
        if systems_created_counter > 0:
            if systems_created_counter  == 1:
                messages.success(request, str(systems_created_counter) + ' system was created.')
            else:
                messages.success(request, str(systems_created_counter) + ' systems were created.')
        if systems_updated_counter > 0:
            if systems_updated_counter  == 1:
                messages.success(request, str(systems_updated_counter) + ' system was updated.')
            else:
                messages.success(request, str(systems_updated_counter) + ' systems were updated.')
        if systems_skipped_counter > 0:
            if systems_skipped_counter  == 1:
                messages.warning(request, str(systems_skipped_counter) + ' system was skipped.')
            else:
                messages.warning(request, str(systems_skipped_counter) + ' systems were skipped.')

        # call logger
        debug_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV_END")

        return redirect(reverse('system_list'))

    else:
        # show empty form
        form = SystemImporterFileCsv()

        # call logger
        debug_logger(str(request.user), " SYSTEM_IMPORTER_FILE_CSV_ENTERED")

    return render(request, 'dfirtrack_main/system/system_importer_file_csv.html', {'form': form})

@login_required(login_url="/login")
def system_ip(request):
    """ this function parses a csv file and tries to import systems and corresponding ips """

    # form was valid to post
    if request.method == "POST":

        # call logger
        debug_logger(str(request.user), " SYSTEM_IP_IMPORTER_BEGIN")

        # get text out of file (variable results from request object via file upload field)
        systemipcsv = TextIOWrapper(request.FILES['systemipcsv'].file, encoding=request.encoding)

        # read rows out of csv
        rows = csv.reader(systemipcsv, quotechar="'")

        # set row counter (needed for logger)
        i = 0

        # check for wrong file type
        try:
            # iterate over rows
            for row in rows:

                # autoincrement row counter
                i += 1

                # check for empty rows
                try:
                    # check system column for empty value
                    if row[0] == '':
                        warning_logger(str(request.user), " SYSTEM_IP_IMPORTER_SYSTEM_COLUMN " + "row_" + str(i) + ":empty_column")
                        continue
                except IndexError:
                    warning_logger(str(request.user), " SYSTEM_IP_IMPORTER_ROW row_" + str(i) + ":empty_row")
                    continue

                # check system column for string
                if not isinstance(row[0], str):
                    warning_logger(str(request.user), " SYSTEM_IP_IMPORTER_SYSTEM_COLUMN " + "row_" + str(i) + ":no_string")
                    continue

                # check system column for length of string
                if len(row[0]) > 50:
                    warning_logger(str(request.user), " SYSTEM_IP_IMPORTER_SYSTEM_COLUMN " + "row_" + str(i) + ":long_string")
                    continue

                # check ip column for ip
                try:
                    ipaddress.ip_address(row[1])
                except ValueError:
                    warning_logger(str(request.user), " SYSTEM_IP_IMPORTER_IP_COLUMN " + "row_" + str(i) + ":invalid_ip")
                    continue

                # create ip
                ip, created = Ip.objects.get_or_create(ip_ip=row[1])
                if created == True:
                    ip.logger(str(request.user), " SYSTEMS_IP_IMPORTER_IP_CREATED")

                # check for existence of system
                system = System.objects.filter(system_name = row[0], ip = ip)
                if system.count() > 0:
                    error_logger(str(request.user), " SYSTEM_IP_IMPORTER_SYSTEM_EXISTS " + "row_" + str(i) + ":system_exists|system_name:" + row[0] + "|ip:" + str(row[1]))
                    continue

                # create form with request data
                form = SystemIpFileImport(request.POST, request.FILES)

                # create system
                if form.is_valid():

                    # don't save form yet
                    system = form.save(commit=False)

                    # set system_name
                    system.system_name = row[0]

                    # set auto values
                    system.system_created_by_user_id = request.user
                    system.system_modified_by_user_id = request.user
                    system.system_modify_time = timezone.now()

                    # save object
                    system.save()

                    # save manytomany
                    form.save_m2m()

                    # save ip for system
                    system.ip.add(ip)

                    # call logger
                    system.logger(str(request.user), ' SYSTEM_IP_IMPORTER_EXECUTED')

        # wrong file type
        except UnicodeDecodeError:
            critical_logger(str(request.user), " SYSTEM_IP_IMPORTER_WRONG_FILE_TYPE")

        # call logger
        debug_logger(str(request.user), " SYSTEM_IP_IMPORTER_END")

        return redirect(reverse('system_list'))

    else:
        # show empty form
        form = SystemIpFileImport(initial={
            'systemstatus': 2,
            'analysisstatus': 1,
        })

        # call logger
        debug_logger(str(request.user), " SYSTEM_IP_IMPORTER_ENTERED")
    return render(request, 'dfirtrack_main/system/system_ip_importer.html', {'form': form})


@login_required(login_url="/login")
def system_tag(request):
    """ this function imports a csv file with multiple systems and relevant tags """

    """
    the following high-level workflow is done by this function
    - remove all tags for systems beginning with 'TAGPREFIX' (if there are any)
    - evaluate given CSV line by line (without first row)
        - check whether this line has relevant tags (leave loop if not)
        - get hostname and convert to lowercase
        - get domain and change to empty string if incorrect (either 'NT AUTHORITY' or hostname itself)
        - create domain if necessary
        - check for existing systems (with this hostname)
            - if == 1:
                - check for existing domain (for this system)
                    if domain_of_system == NULL: domain is set to domain from CSV (if there is one)
            - if > 1: leave loop because not distinct
            - if == 0: create system
        - add relevant tags to this system
        - check for reportitem headline = SYSTEMTAG_HEADLINE, reportitem_subheadline = SYSTEMTAG_SUBHEADLINE and create if necessary
        - fill reportitem_note with markdown table containing with information of report(s)
    - logs and messages are written if applicable
    - counters are incremented where necessary
    """

    # form was valid to post
    if request.method == "POST":

        # call logger
        debug_logger(str(request.user), " SYSTEM_TAG_IMPORTER_BEGIN")

        # check TAGLIST (from settings.config) for empty list
        if not TAGLIST:
            messages.error(request, "No relevant tags defined. Check `TAGLIST` in `dfirtrack.config`!")
            # call logger
            error_logger(str(request.user), " SYSTEM_TAG_IMPORTER_NO_TAGS_DEFINED.")
            return redirect('/system/')
        else:
            taglist = TAGLIST

        # check TAGPREFIX (from settings.config) for empty string
        if TAGPREFIX is "":
            messages.error(request, "No prefix string defined. Check `TAGPREFIX` in `dfirtrack.config`!")
            # call logger
            error_logger(str(request.user), " SYSTEM_TAG_IMPORTER_NO_TAGPREFIX_DEFINED.")
            return redirect('/system/')
        # expand the string by an underscore
        else:
#            tagprefix = TAGPREFIX + "_"
            tagprefix = TAGPREFIX + "-"

        # create tagaddlist to append for every new system
        tagaddlist = []
        for tag in taglist:
                tagaddlist.append(tagprefix + tag)

#        # check whether SYSTEMTAG_HEADLINE is defined in `dfirtrack.config`
#        if systemtag_headline == '':
#            # call logger
#            error_logger(str(request.user), " SYSTEMTAG_HEADLINE_VARIABLE_UNDEFINED")
#            messages.error(request, "The variable SYSTEMTAG_HEADLINE seems to be undefined. Check `dfirtrack.config`!")
#            # leave importer
#            return redirect('/systems/')
#
#        # check whether SYSTEMTAG_SUBHEADLINE is defined in `dfirtrack.config`
#        if systemtag_subheadline == '':
#            # call logger
#            error_logger(str(request.user), " SYSTEMTAG_SUBHEADLINE_VARIABLE_UNDEFINED")
#            messages.error(request, "The variable SYSTEMTAG_SUBHEADLINE seems to be undefined. Check `dfirtrack.config`!")
#            # leave importer
#            return redirect('/systems/')

        # get text out of file (variable results from request object via file upload field)
        systemtagcsv = TextIOWrapper(request.FILES['systemtagcsv'].file, encoding=request.encoding)

        # read rows out of csv
        rows = csv.reader(systemtagcsv)

        # create empty list (this list is used to store every line as single dict: {system_name: row}), because if there are multiple rows with the same system they are added to the same reportitem
#        rowlist = []

#        """ remove all tags for systems beginning with 'TAGPREFIX' (if there are any) """
#
#        # get all systems that have tags beginning with 'TAGPREFIX' | prefixtagsystems -> queryset
#        prefixtagsystems=System.objects.filter(tag__tag_name__startswith=tagprefix)
#
#        # iterate over systems in queryset | prefixtagsystem  -> system object
#        for prefixtagsystem in prefixtagsystems:
#
#            # get all tags beginning with 'TAGPREFIX' that belong to the actual system | systemprefixtags -> queryset
#            systemprefixtags=prefixtagsystem.tag.filter(tag_name__startswith=tagprefix)
#
#            # iterate over queryset | systemprefixtag -> tag object
#            for systemprefixtag in systemprefixtags:
#                # delete all existing tags (the m2m relationship) beginning with 'TAGPREFIX' for this system (so that removed tags from csv will be removed as well)
#                systemprefixtag.system_set.remove(prefixtagsystem)
#
#        # create headline if it does not exist
#        headline, created = Headline.objects.get_or_create(headline_name=systemtag_headline)
#        if created == True:
#            headline.logger(str(request.user), " SYSTEMS_TAG_IMPORTER_HEADLINE_CREATED")
#
#        """ remove all reportitems """
#
#        # delete reportitems (so no reportitems with legacy information / tags will be left)
#        Reportitem.objects.filter(headline = headline, reportitem_subheadline = systemtag_subheadline).delete()

        """ prepare and start loop """

        # set row_counter (needed for logger)
        row_counter = 1

        # set systems_created_counter (needed for messages)
        systems_created_counter = 0

        # set systems_skipped_counter (needed for messages)
        systems_skipped_counter = 0

        # iterate over rows
        for row in rows:

            # skip first row (headlines)
            if row_counter == 1:
                # autoincrement row counter
                row_counter += 1
                continue

#            # get system_name and change to lowercase
#            system_name = row[8].lower()
            # get system_name
            system_name_full = row[0]
            system_name_without_domain = system_name_full.split('.')[0]
            system_name_without_timestamp = system_name_without_domain.split('_')[0]
            system_name = system_name_without_timestamp

#            # get tags from csv
#            tagcsvstring = row[9]
#            if tagcsvstring == '':
#                # autoincrement systems_skipped_counter
#                systems_skipped_counter += 1
#                # autoincrement row_counter
#                row_counter += 1
#                # leave because systems without tags are not relevant
#                continue
#            else:
#                # convert string (at whitespaces) to list
#                tagcsvlist = tagcsvstring.split()

#            # create empty list for mapping
#            tagaddlist = []
#            # check for relevant tags and add to list
#            for tag in taglist:
#                if tag in tagcsvlist:
#                    tagaddlist.append(tagprefix + tag)
#
#            # check if tagaddlist is empty
#            if not tagaddlist:
#                # autoincrement systems_skipped_counter
#                systems_skipped_counter += 1
#                # autoincrement row_counter
#                row_counter += 1
#                # leave because there are no relevant tags
#                continue
#
#            # get domain from csv
#            domain_name = row[7]
#            # change domain_name to empty string if incorrect domain_name ('NT AUTHORITY') was provided
#            if domain_name == 'NT AUTHORITY':
#                domain_name = ''
#            # clear domain if domain_name equals system_name
#            elif domain_name.lower() == system_name:
#                domain_name = ''

#            # get or create domain object if some valid name was provided
#            if domain_name != '':
#                # create domain
#                domain, created = Domain.objects.get_or_create(domain_name=domain_name)
#                # call logger if created
#                if created == True:
#                    domain.logger(str(request.user), " SYSTEMS_TAG_IMPORTER_DOMAIN_CREATED")
#                    messages.success(request, 'Domain "' + domain.domain_name + '" created.')
#            else:
#                # set domain to None to avoid further errors (domain is needed later)
#                domain = None

#            # create empty dict
#            rowdict = {}
#
#            # put the actual row to the dict (dict with only ONE key-value-pair)
#            rowdict[system_name] = row
#
#            # append dict to the global list (because if there are multiple rows with the same system, needed for reportitem SYSTEMTAG_SUBHEADLINE)
#            rowlist.append(rowdict)

            # get all systems with this system_name
            systemquery = System.objects.filter(system_name=system_name)

            """ check how many systems were returned """

            # if there is only one system
            if len(systemquery) == 1:
                # autoincrement systems_skipped_counter
                systems_skipped_counter += 1
#                # get system object
#                system = System.objects.get(system_name=system_name)
#
#                """ add domain from CSV only if system does not already has a domain """
#
#                # check whether system has existing domain and CSV submitted a domain
#                if system.domain is None and domain is not None:
#
#                    # if system has no existing domain set domain of system to domain submitted by tag csv
#                    system.domain = domain
#                    system.system_modify_time = timezone.now()
#                    system.system_modified_by_user_id = request.user
#                    system.save()
#                    # call logger
#                    system.logger(str(request.user), " SYSTEMS_TAG_IMPORTER_SYSTEM_DOMAIN_ADDED")

            # if there is more than one system
            elif len(systemquery) > 1:
                # call logger
                error_logger(str(request.user), " SYSTEM_TAG_IMPORTER_SYSTEM_EXISTS_MULTIPLE_TIMES " + "row_" + str(row_counter) + ":system_exists_multiple_times|system_name:" + system_name)
                messages.error(request, 'System "' + system_name + '" was found multiple times. Nothing was changed for this system.')
                # autoincrement row_counter
                row_counter += 1
                # leave because of no distinct mapping
                continue
            else:
                # create entire new system object
                system = System()
                system.system_name = system_name
#                #system.systemstatus = Systemstatus.objects.get(systemstatus_name = "Unknown")
                system.systemstatus = Systemstatus.objects.get(systemstatus_name = "Analysis ongoing")
#                #system.analysisstatus = Analysisstatus.objects.get(analysisstatus_name = "Needs anaylsis")
                system.analysisstatus = Analysisstatus.objects.get(analysisstatus_name = "Ready for analysis")
#                # add domain if submitted
#                if domain is not None:
#                    system.domain = domain
                system.system_modify_time = timezone.now()
                system.system_created_by_user_id = request.user
                system.system_modified_by_user_id = request.user
                system.save()

                # autoincrement systems_created_counter
                systems_created_counter += 1

                # call logger
                system.logger(str(request.user), " SYSTEMS_TAG_IMPORTER_SYSTEM_CREATED")

                # create ip
                ip, created = Ip.objects.get_or_create(ip_ip=row[12])
                if created == True:
                    ip.logger(str(request.user), " SYSTEMS_TAG_IMPORTER_IP_CREATED")
                ip.system_set.add(system)

                # get errors
                if not row[10]:
                    # continue if there is an empty string
                    pass
                else:
                    # get object
                    tag_error = Tag.objects.get(tag_name=tagprefix + 'Error')
                    # add error tag to system
                    tag_error.system_set.add(system)

                # iterate over tags in tagaddlist
                for tag_name in tagaddlist:
                    # get object
                    tag = Tag.objects.get(tag_name=tag_name)
                    # add tag to system
                    tag.system_set.add(system)
#                # get tagcolor object
#                tagcolor = Tagcolor.objects.get(tagcolor_name='primary')
#
#                # create tag if needed
#                tag, created = Tag.objects.get_or_create(tag_name=tag_name, tagcolor=tagcolor)
#                # call logger if created
#                if created == True:
#                    tag.logger(str(request.user), " SYSTEMS_TAG_IMPORTER_TAG_CREATED")
#                    messages.success(request, 'Tag "' + tag.tag_name + '" created.')
#
#                # add tag to system
#                tag.system_set.add(system)

                # call logger
                system.logger(str(request.user), " SYSTEMS_TAG_IMPORTER_SYSTEM_MODIFIED")

#            # create reportitem if it does not exist (get_or_create won't work in this context because of needed user objects for saving)
#            try:
#                reportitem = Reportitem.objects.get(system = system, headline = headline, reportitem_subheadline = systemtag_subheadline)
#            except Reportitem.DoesNotExist:
#                reportitem = Reportitem()
#                reportitem.system = system
#                reportitem.headline = headline
#                reportitem.reportitem_subheadline = (systemtag_subheadline)
#                reportitem.reportitem_created_by_user_id = request.user
#
#            # create empty list (used to store elements of markdown table)
#            notelist = []
#
#            # put head of markdown table into list
#            notelist.append("|File|Type|Version|Started|Duration|Lines|Checked|Domain|Host|Tags|Errors|FirstTrace|LastToolUsage|UsageTime|MalwareInstall")
#            notelist.append("|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|")
#
#            # iterate over entries in list (dictionaries)
#            for item in rowlist:
#                # if this single key-value-pair dict contains the system
#                if system_name in item:
#                    # get row
#                    entry = item[system_name]
#                    # convert row
#                    entry = "|" + "|".join(entry) + "|"
#                    # fill empty fields with '---' (otherwise mkdocs skips these)
#                    entry = entry.replace("||", "| --- |")
#                    # repeat last step to catch empty fields lying next to each other
#                    entry = entry.replace("||", "| --- |")
#                    # put entry to markdown table
#                    notelist.append(entry)
#
#            # join list to string with linebreaks
#            notestring = "\n".join(notelist)
#
#            # add changing values (existing reportitem_note will be overwritten)
#            reportitem.reportitem_note = notestring
#            reportitem.reportitem_modified_by_user_id = request.user
#            reportitem.save()
#
#            # call logger
#            reportitem.logger(str(request.user), " SYSTEMS_TAG_IMPORTER_REPORTITEM_CREATED_OR_MODIFIED")
#
#            # autoincrement row_counter
#            row_counter += 1

        # call final messages
        if systems_created_counter > 0:
            if systems_created_counter  == 1:
                messages.success(request, str(systems_created_counter) + ' system was created.')
            else:
                messages.success(request, str(systems_created_counter) + ' systems were created.')
        if systems_skipped_counter > 0:
            if systems_skipped_counter  == 1:
                #messages.warning(request, str(systems_skipped_counter) + ' system was skipped or cleaned (no relevant tags).')
                messages.warning(request, str(systems_skipped_counter) + ' system was skipped (already existent).')
            else:
                #messages.warning(request, str(systems_skipped_counter) + ' systems were skipped or cleaned (no relevant tags).')
                messages.warning(request, str(systems_skipped_counter) + ' systems were skipped (already existent).')

        # call logger
        debug_logger(str(request.user), " SYSTEM_TAG_IMPORTER_END")

        return redirect(reverse('system_list'))

    else:
        # show empty form
        form = SystemTagFileImport()

        # call logger
        debug_logger(str(request.user), " SYSTEM_TAG_IMPORTER_ENTERED")

    return render(request, 'dfirtrack_main/system/system_tag_importer.html', {'form': form})
