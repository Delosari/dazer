import os
import sys
import numpy as np
import pyneb as pn
import pyCloudy as pc
import matplotlib.pyplot as plt

def query_file_location(question, default_address):

    """
    This function asks for a location file address from the command terminal
    it checks if the file exists before proceeding with the code
    "question" is a string that is presented to the user.
    "default_address" is the presumed file location.
    """

    while True:
        if default_address == None:
            prompt = '{}:'.format(question, default_address)
        else:
            prompt = '{} [{}]'.format(question, default_address)

        sys.stdout.write(prompt)
        input_address = raw_input()
        if default_address is not None and input_address == '':
            input_address = default_address
        if os.path.isfile(input_address):
            return input_address
        else:
            print 'sorry no file was found at that location\n'


def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")


def large_H_He_orders_grid(temp, dens, model_name, H_He_lines_labels):
    logTe = np.log10(temp)
    logne = np.log10(dens)
    cloudy_model = pc.CloudyInput(model_name)
    cloudy_model.set_other(('init file "hheonly.ini"'))
    cloudy_model.set_other(('element helium abundance -3'))
    cloudy_model.set_BB(Teff=Teff, lumi_unit='q(H)', lumi_value=qH)
    cloudy_model.set_radius(r_in=dist)
    cloudy_model.set_other(('constant temperature {}'.format(logTe)))
    cloudy_model.set_cste_density(logne)
    cloudy_model.set_other(('database H-like levels large element hydrogen'))
    cloudy_model.set_other(('database H-like levels large element helium'))
    cloudy_model.set_other(('set dr 0'))
    cloudy_model.set_stop(('zone 1'))
    cloudy_model.set_emis_tab(H_He_lines_labels)
    cloudy_model.print_input()
    return cloudy_model


def declare_output_files():

    """
    This method establishes the output files from pycloudy grids
    For these simulations in which we are only want to calculate the emissivities from the hydrogen and helium lines
    most of the default files from pycloudy outputs are not required
    :return:
    """

    #Exclude these files from being generated by the simulations
    components_remove = [#['radius', '.rad'],
                         #['continuum', '.cont'],
                         #['physical conditions', '.phy'],
                         ['overview', '.ovr'],
                         ['heating', '.heat'],
                         ['cooling', '.cool'],
                         ['optical depth', '.opd']]
    for item in components_remove:
        pc.config.SAVE_LIST.remove(item)

    #Exclude these elements files from being generated by the simulations
    elements_remove = [#['hydrogen','.ele_H'],
                       #['helium','.ele_He'],
                       ['carbon', '.ele_C'],
                       ['nitrogen', '.ele_N'],
                       ['oxygen', '.ele_O'],
                       ['argon', '.ele_Ar'],
                       ['neon', '.ele_Ne'],
                       ['sulphur', '.ele_S'],
                       ['chlorin', '.ele_Cl'],
                       ['iron', '.ele_Fe'],
                       ['silicon', '.ele_Si']]
    for item in elements_remove:
        pc.config.SAVE_LIST_ELEMS.remove(item)

    return

# Results are be stored at a root defined from the .py file address
dir_ = os.path.dirname(os.path.realpath(__file__))

# Start to define cloudy simulation grid:
model_name      = 'emissivity_grid'
full_model_name = '{0}{1}'.format(dir_, model_name)

# Physical parameters
Teff    = 45000.    #K
qH      = 47.0      #s-1
dist    = 16.0      #kpc

# Temperature and density interval for the grid
Te_interval = [9000.0, 9500.0, 10000.0, 10500.0]
ne_interval = [100.0]

# Lines emissivities to be saved from the compuation
labels_list = ['H  1 4861.33A',
                'H  1 6562.81A',
                'HE 1 3888.63A',
                'HE 1 4026.20A',
                'HE 1 4471.49A',
                'HE 1 5875.64A',
                'HE 1 6678.15A',
                'HE 1 7065.22A']

# Create a folder to results the data
dir_results = '{}/helium_emissivities/'.format(dir_)
if not os.path.exists(dir_results):
    os.makedirs(dir_results)

# Check if the cloudy executable address had been saved before
address_cloudy_exe_storage = '{}/cloudy_exe_loc.txt'.format(dir_results)
if os.path.isfile(address_cloudy_exe_storage):
    with open(address_cloudy_exe_storage, 'r') as f:
        cloudy_address = f.read()
else:
    cloudy_address = None

# Confirm cloudy execurable addres
pc.config.cloudy_exe = query_file_location('-Please type the cloudy executable address and press enter', cloudy_address)

# Save cloudy executable location for future runs
with open(address_cloudy_exe_storage, 'w') as f:
    f.write(cloudy_address)

# Exclude extra files from being generated by the output
declare_output_files()

# Run cloudy grids
start_simulation_check = query_yes_no('-The data is ready, Do you want to run the {}x{} grid?'.format(len(Te_interval), len(ne_interval)), default='no')
if start_simulation_check:
    for Te in Te_interval:
        for ne in ne_interval:
            model_name = 'M_i_Te{}_ne{}'.format(Te, ne)
            model_i = large_H_He_orders_grid(Te, ne, dir_results + model_name, labels_list)
            print '\nRunning model: ', model_name
            model_i.run_cloudy()
            pc.log_.timer('-Cloudy script run @ {}. Process ended after:'.format(dir_results), calling='log')

# --This code section generates some plots on the results to compare the results with the emissivities from Porter et al 2012-13
#Loading simulation results
Ms = pc.load_models(dir_results, verbose=False)

#Reading the physical parameters in vector form
Te_vector = np.empty(len(Ms))
ne_vector = np.empty(len(Ms))
emis_dict = {label: np.empty(len(Ms)) for label in labels_list}

for i in range(len(Ms)):
    Te_vector[i] = Ms[i].T0
    ne_vector[i] = Ms[i].ne
    for j in range(len(emis_dict)):
        line_label = labels_list[j].replace(' ', '_').replace('.', '')
        emis_dict[labels_list[j]][i] = Ms[i].get_emis(line_label)
    print '\nStats', Ms[i].T0, Ms[i].ne
    print Ms[i].print_stats()

#Sort the output models according to increasing temperature
idx_sort = np.argsort(Te_vector)

#Generate H1 and He1 pyneb object
H1 = pn.RecAtom('H', 1)
He1 = pn.RecAtom('He', 1)

#Choose a line:
line_label  = 'HE 1 5875.64A'
line_dict   = {'HE 1 5875.64A':'5876.0'}

HeI_line_pn = He1.getEmissivity(Te_vector[idx_sort], ne_vector[idx_sort], label=line_dict[line_label], product=False)
HI_Beta_pn = H1.getEmissivity(Te_vector[idx_sort], ne_vector[idx_sort], label='4_2', product=False)

HeI_line_cl = emis_dict[line_label][idx_sort]
HI_Beta_cl = emis_dict['H  1 4861.33A'][idx_sort]

print 'Temp vector', Te_vector[idx_sort]

print 'Pyneb ratio', HeI_line_pn/HI_Beta_pn
print 'Cloudy ratio', HeI_line_cl/HI_Beta_cl

print 'Cloudy Hbeta', HI_Beta_cl
print 'Pyneb Hbeta', HI_Beta_pn

print 'Pyneb HeI 5876 Te 10000.0 ne 100', He1.getEmissivity(10000.0, 100.0, label='5876.0')#, '->', He1.getEmissivity(10000.0, 100.0, label='5876.0')
print 'Cloudy HeI 5876 Te 10000.0 ne 100', HeI_line_cl[2]# , '->',HeI_line_cl[2]

print 'Pyneb Hbeta Te 10000.0 ne 100', H1.getEmissivity(10000.0, 100.0, label='4_2')#, '->', H1.getEmissivity(10000.0, 100.0, label='4_2')
print 'Cloudy Hbeta Te 10000.0 ne 100', emis_dict['H  1 4861.33A'][idx_sort][2]#, '->', emis_dict['H  1 4861.33A'][idx_sort][2]


# #Generate the plot
# fig, ax = plt.subplots()
# ax.plot(Te_vector[idx_sort], HeI_line_pn/HI_Beta_pn, label='Pyneb: ' + line_label)
# ax.plot(Te_vector[idx_sort], HeI_line_cl/HI_Beta_cl, label='Cloudy: ' + line_label)
# ax.legend()
# ax.update({'xlabel':'Emissivity', 'ylabel':'y', 'title':'Helium lines emissivity comparison'})
# plt.show()

