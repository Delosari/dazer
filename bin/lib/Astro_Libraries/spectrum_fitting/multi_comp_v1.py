from os                                     import path, name, makedirs
from sys                                    import argv,exit
from pyneb                                  import atomicData, RecAtom, Atom
from collections                            import OrderedDict
from scipy.interpolate import interp1d
from uncertainties.unumpy                   import nominal_values, std_devs
from lib.Astro_Libraries.Nebular_Continuum  import NebularContinuumCalculator
from lib.Astro_Libraries.Reddening_Corrections import ReddeningLaws
from lib.ssp_functions.ssp_synthesis_tools  import ssp_fitter, ssp_synthesis_importer
from DZ_LineMesurer                         import LineMesurer_v2
from numpy import array, loadtxt, genfromtxt, copy, isnan, arange, insert, concatenate, mean, std, power, exp, zeros, \
    square, empty, percentile, random, median, ones, isnan, sum as np_sum, transpose, vstack, savetxt, delete, where, \
    searchsorted, in1d, save as np_save, load as np_load
import pymc as pymc2
from timeit                                 import default_timer as timer
from uncertainties import ufloat
from pandas import read_excel, read_csv
from bisect import bisect_left
from lib.Plotting_Libraries.dazer_plotter   import Plot_Conf

def make_folder(folder_path):

    #TODO This one is only valid for 2.7
    #TODO add this one to your collection
    try:
        makedirs(folder_path)
    except OSError:
        if not path.isdir(folder_path):
            raise

    return

def import_table_data(address, columns):

    Imported_Array = genfromtxt(address, dtype=float, usecols = columns, skip_header = 2).T
    Datarray = Imported_Array[:,~isnan(Imported_Array).all(0)]

    return Datarray

def correct_df_row_name(df, lines_to_cor):

    list_index = df.index.tolist()

    for i in range(len(lines_to_cor)):
        if lines_to_cor[i][0] in list_index:
            idx_i = list_index.index(lines_to_cor[i][0])
            list_index[idx_i] = lines_to_cor[i][1]

    df.index = list_index

    return df

def bilinear_interpolator_axis(x, y, x_range, y_range, data_grid):
    # TODO Check this emissivity interpolation with pyneb

    i = bisect_left(x_range, x) - 1
    j = bisect_left(y_range, y) - 1

    x1, x2 = x_range[i:i + 2]
    y1, y2 = y_range[j:j + 2]

    z11, z12 = data_grid[j][i:i + 2]
    z21, z22 = data_grid[j + 1][i:i + 2]

    inter_value = (z11 * (x2 - x) * (y2 - y) +
                   z21 * (x - x1) * (y2 - y) +
                   z12 * (x2 - x) * (y - y1) +
                   z22 * (x - x1) * (y - y1)) / ((x2 - x1) * (y2 - y1))

    return inter_value

def load_emissivity_grid(grid_address):

    emis_grid = np_load(grid_address)

    return emis_grid

def save_emissivity_grid(grid_address, grid):

    np_save(grid_address ,grid)

    return

def generate_emissivity_grid(pynebcode_list, ions_list, ion_dict, temp_interval, den_interval):

    grid_emis = empty((len(temp_interval), len(den_interval), len(pynebcode_list)))

    for i in range(len(pynebcode_list)):
        ion = ions_list[i]
        grid_emis[:, :, i] =ion_dict[ion].getEmissivity(temp_interval, den_interval, wave=pynebcode_list[i],product=True)

    return grid_emis

class Import_model_data(ssp_synthesis_importer):

    '''
    This class loads the binaries required for the dazer spectra synthesizer module
    '''


    def __init__(self):

        #Class with tools to import starlight bases
        ssp_synthesis_importer.__init__(self)

        self.paths_dict = {}

        # Paths for linux:
        if name == 'posix':
            # TODO This data should be read from a text file
            self.paths_dict['inference_folder']     = '/home/vital/Astrodata/Inference_output/'
            self.paths_dict['nebular_data_folder']  = '/home/vital/Dropbox/Astrophysics/Lore/NebularContinuum/'
            self.paths_dict['Hydrogen_CollCoeff']   = '/home/vital/workspace/dazer/bin/lib/Astro_Libraries/Neutral_Hydrogen_Collisional_Correction_coef.txt'
            self.paths_dict['Helium_CollCoeff']     = '/home/vital/workspace/dazer/bin/lib/Astro_Libraries/Neutral_Helium_Collisional_Correction_coef.txt'
            self.paths_dict['Helium_OpticalDepth']  = '/home/vital/workspace/dazer/bin/lib/Astro_Libraries/Helium_OpticalDepthFunction_Coefficients.txt'
            self.paths_dict['lines_data_file']      = '/home/vital/PycharmProjects/dazer/bin/lib/Astro_Libraries/spectrum_fitting/lines_data.xlsx'
            self.paths_dict['dazer_path']           = '/home/vital/workspace/dazer/'
            self.paths_dict['stellar_data_folder']  = '/home/vital/Starlight/'
            self.paths_dict['observations_folder']  = '/home/vital/Dropbox/Astrophysics/Data/WHT_observations/objects/'
            self.paths_dict['recomb_grid']          = '/home/vital/PycharmProjects/dazer/bin/lib/Astro_Libraries/spectrum_fitting/recomb_grid.npy'
            self.paths_dict['collext_grid']         = '/home/vital/PycharmProjects/dazer/bin/lib/Astro_Libraries/spectrum_fitting/collext_grid.npy'

        # Paths for windows:
        elif name == 'nt':
            # TODO Check guides for windows and linux
            self.paths_dict['inference_folder']     = 'D:/Inference_data/'
            self.paths_dict['nebular_data_folder']  = 'E:/Cloud Storage/Dropbox/Astrophysics/Lore/NebularContinuum/'
            self.paths_dict['Hydrogen_CollCoeff']   = 'C:/Users/lativ/git/dazer/bin/lib/Astro_Libraries/Neutral_Hydrogen_Collisional_Correction_coef.txt'
            self.paths_dict['Helium_CollCoeff']     = 'C:/Users/lativ/git/dazer/bin/lib/Astro_Libraries/Neutral_Helium_Collisional_Correction_coef.txt'
            self.paths_dict['Helium_OpticalDepth']  = 'C:/Users/lativ/git/dazer/bin/lib/Astro_Libraries/Helium_OpticalDepthFunction_Coefficients.txt'
            self.paths_dict['stellar_data_folder']  = 'E:/Cloud Storage/Dropbox/Astrophysics/Tools/Starlight/'
            self.paths_dict['lines_data_file']      = 'C:/Users/lativ/git/dazer/bin/lib/Astro_Libraries/spectrum_fitting/lines_data.xlsx'
            self.paths_dict['dazer_path']           = 'C:/Users/lativ/git/dazer/'
            self.paths_dict['observations_folder']  = 'E:/Cloud Storage/Dropbox/Astrophysics/Data/WHT_observations/objects/'
            self.paths_dict['recomb_grid']          = 'C:/Users/lativ/git/dazer/bin/lib/Astro_Libraries/spectrum_fitting/recomb_grid.npy'
            self.paths_dict['collext_grid']         = 'C:/Users/lativ/git/dazer/bin/lib/Astro_Libraries/spectrum_fitting/collext_grid.npy'

        # Import database with lines labels information
        self.lines_df = read_excel(self.paths_dict['lines_data_file'], sheetname=0, header=0, index_col=0)

        # Additional code to adapt to old lines log labelling
        self.lines_df['pyneb_code'] = self.lines_df['pyneb_code'].astype(str)
        idx_numeric_pynebCode = ~self.lines_df['pyneb_code'].str.contains('A+')
        self.lines_df.loc[idx_numeric_pynebCode, 'pyneb_code'] = self.lines_df.loc[idx_numeric_pynebCode, 'pyneb_code'].astype(int)
        self.lines_df['ion'].apply(str)

    def import_optical_depth_coeff_table(self, helium_lines):

        Data_dict = OrderedDict()

        for i in range(len(helium_lines)):

            Line = helium_lines[i]

            # TODO addapt the table to make sure it can read both objects H13889A_label
            Data_dict[Line] = loadtxt(self.paths_dict['Helium_OpticalDepth'], dtype=float, skiprows=2, usecols=(i,))


            # if Line != self.H13889A_label:
            #     Data_dict[Line] = loadtxt(self.paths_dict['Helium_OpticalDepth'], dtype = float, skiprows = 2, usecols = (i,))
            #
            # else:
            #     Data_dict[self.He3889_label] = loadtxt(self.paths_dict['Helium_OpticalDepth'], dtype = float, skiprows = 2, usecols = (i,))

        return Data_dict

    def load_obs_data(self, lineslog_df, obj_series, obj_name, obj_wave, obj_flux, valid_lines, extension_treat='', Deblend_Check=True):

        # Correction from new to old indexes
        corr_pairs = [('H1_4340A', 'H1_4341A'), ('He1_4472A', 'He1_4471A')]
        lineslog_df = self.correct_df_row_name(lineslog_df, corr_pairs)

        # Append the pyneb_code and label
        lineslog_df['pyneb_code'] = None
        lineslog_df['ion'] = None
        lineslog_df['wavelength'] = 0.0
        for row_name in self.lines_df.index:
            lineslog_df.loc[row_name, 'pyneb_code'] = self.lines_df.loc[row_name, 'pyneb_code']
            lineslog_df.loc[row_name, 'ion'] = self.lines_df.loc[row_name, 'ion']
            lineslog_df.loc[row_name, 'wavelength'] = self.lines_df.loc[row_name, 'wavelength']

        # Nitrogen line does not have error (wide component)
        lineslog_df.loc['N2_6548A', 'line_Flux'] = lineslog_df.loc['N2_6584A', 'line_Flux'] / 3.0

        # Empty dictionary to store the data
        self.obj_data = {}

        # Resample object wavelength and flux
        wmin, wmax = int(obj_wave[0]) + 1, 6900
        norm_interval = (5100, 5150)

        # Resample observation
        obj_wave_resam = arange(wmin, wmax, 1, dtype=float)
        obj_flux_resam = interp1d(obj_wave, obj_flux, bounds_error=True)(obj_wave_resam)

        # Normalize  observation
        idx_Wavenorm_min, idx_Wavenorm_max = searchsorted(obj_wave, norm_interval)
        normFlux_obj = median(obj_flux[idx_Wavenorm_min:idx_Wavenorm_max])
        obj_flux_norm = obj_flux_resam / normFlux_obj

        # Hbeta_data
        idx_Hbeta = lineslog_df.index == 'H1_4861A'
        self.obj_data['Hbeta_Flux'] = nominal_values(lineslog_df.loc[idx_Hbeta, 'line_Flux'].values[0])
        self.obj_data['Hbeta_err'] = std_devs(lineslog_df.loc[idx_Hbeta, 'line_Flux'].values[0])
        self.Halpha_norm = nominal_values(lineslog_df.loc['H1_6563A', 'line_Flux']) / normFlux_obj

        # ----Get recombination lines
        self.ready_lines_data('H1', valid_lines['H1'])
        self.ready_lines_data('He1', valid_lines['He1'])

        obsRecomb_lines = valid_lines['H1'] + valid_lines['He1']

        self.n_recombLines = len(obsRecomb_lines)
        self.range_recombLines = arange(self.n_recombLines)

        self.obs_recomb_fluxes = nominal_values(
            lineslog_df.loc[lineslog_df.index.isin(obsRecomb_lines)].line_Flux.values) / self.obj_data['Hbeta_Flux']
        self.obs_recomb_err = std_devs(lineslog_df.loc[lineslog_df.index.isin(obsRecomb_lines)].line_Flux.values) / \
                              self.obj_data['Hbeta_Flux']

        self.Recomb_labels = lineslog_df.loc[lineslog_df.index.isin(obsRecomb_lines)].index.values
        self.Recomb_pynebCode = self.lines_df.loc[self.lines_df.index.isin(obsRecomb_lines)].pyneb_code.values

        idx_recomb = lineslog_df.index.isin(obsRecomb_lines)
        self.obj_data['recombLine_labes'] = lineslog_df.loc[idx_recomb].index.values
        self.obj_data['recombLine_ions'] = lineslog_df.loc[idx_recomb].ion.values
        self.obj_data['recombLine_waves'] = lineslog_df.loc[idx_recomb].wavelength.values
        self.obj_data['recombLine_pynebCode'] = lineslog_df.loc[idx_recomb].pyneb_code.values
        self.obj_data['recombLine_flambda'] = self.reddening_Xx(self.obj_data['recombLine_waves'],
                                                                self.reddedning_curve_model,
                                                                self.Rv_model) / self.Hbeta_xX - 1.0

        # ----Get collisional excited lines
        self.ready_lines_data('S2', valid_lines['S2'])
        self.ready_lines_data('S3', valid_lines['S3'])
        self.ready_lines_data('O2', valid_lines['O2'])
        self.ready_lines_data('O3', valid_lines['O3'])
        self.ready_lines_data('N2', valid_lines['N2'])
        self.ready_lines_data('Ar3', valid_lines['Ar3'])
        self.ready_lines_data('Ar4', valid_lines['Ar4'])

        obsMetals_lines = valid_lines['S2'] + valid_lines['S3'] + valid_lines['O2'] + valid_lines['O3'] + valid_lines[
            'N2'] + valid_lines['Ar3'] + valid_lines['Ar4']

        self.n_colExcLines = len(obsMetals_lines)
        self.range_colExcLines = arange(self.n_colExcLines)
        self.obs_metal_fluxes = nominal_values(
            lineslog_df.loc[lineslog_df.index.isin(obsMetals_lines)].line_Flux.values) / self.obj_data['Hbeta_Flux']
        self.obs_metal_Error = std_devs(lineslog_df.loc[lineslog_df.index.isin(obsMetals_lines)].line_Flux.values) / \
                               self.obj_data['Hbeta_Flux']

        idx_coll = lineslog_df.index.isin(obsMetals_lines)
        self.obj_data['colLine_labes'] = lineslog_df.loc[lineslog_df.index.isin(obsMetals_lines)].index.values
        self.obj_data['colLine_ions'] = lineslog_df.loc[idx_coll].ion.values
        self.obj_data['colLine_waves'] = lineslog_df.loc[idx_coll].wavelength.values
        self.obj_data['colLine_pynebCode'] = lineslog_df.loc[idx_coll].pyneb_code.values
        self.obj_data['colLine_flambda'] = self.reddening_Xx(self.obj_data['colLine_waves'],
                                                             self.reddedning_curve_model,
                                                             self.Rv_model) / self.Hbeta_xX - 1.0

        # Get physical parameters
        Tlow_key = obj_series['T_low']
        self.obj_data['TSIII'] = obj_series[Tlow_key].nominal_value
        self.obj_data['TSIII_error'] = obj_series[Tlow_key].std_dev

        self.obj_data['nSII'] = obj_series['neSII'].nominal_value
        self.obj_data['nSII_error'] = obj_series['neSII'].std_dev

        self.obj_data['cHbeta'] = obj_series['cHbeta_emis'].nominal_value
        self.obj_data['cHbeta_error'] = obj_series['cHbeta_emis'].std_dev

        self.obj_data['sigma_gas'] = nominal_values(
            lineslog_df.loc[lineslog_df.index.isin(obsRecomb_lines)].sigma.values)

        self.obj_data['z_star'] = 0.0

        print '--Importing physical data'
        print '---{}: {} +/- {}'.format('TSIII', self.obj_data['TSIII'], self.obj_data['TSIII_error'])
        print '---{}: {} +/- {}'.format('nSII', self.obj_data['nSII'], self.obj_data['nSII_error'])
        print '---{}: {} +/- {}'.format('cHbeta', self.obj_data['cHbeta'], self.obj_data['cHbeta_error'])
        print '---{}: {}'.format('sigma_gas', self.obj_data['sigma_gas'])

        # ----Get stellar data (This must go outside)

        # Load stellar libraries
        default_Starlight_file = self.paths_dict['stellar_data_folder'] + 'Dani_Bases_Extra.txt'
        default_Starlight_folder = self.paths_dict['stellar_data_folder'] + 'Bases/'

        self.ssp_lib = self.load_stellar_bases('starlight', default_Starlight_folder, default_Starlight_file, \
                                               resample_int=1, resample_range=(wmin, wmax), norm_interval=norm_interval)

        # Load object mask
        mask_file_address = '{}{}/{}_Mask.lineslog'.format(self.paths_dict['observations_folder'], obj_name, obj_name)

        mask_df = read_csv(mask_file_address, delim_whitespace=True, names=['blue_limit', 'red_limit', 'code', 'label'],
                           skiprows=1)

        # Pixels within the spectrum mask
        boolean_mask = ones(len(obj_wave_resam), dtype=bool)
        for line in mask_df.index:
            wmin, wmax = mask_df.loc[line, 'blue_limit'], mask_df.loc[line, 'red_limit']
            idx_cur_spec_mask = (obj_wave_resam > wmin) & (obj_wave_resam < wmax)
            boolean_mask = boolean_mask & ~idx_cur_spec_mask

        # Load results from first ssp fittings
        populations_coeffs_file = '{}{}/{}_populations_prefit.txt'.format(self.paths_dict['observations_folder'],
                                                                          obj_name, obj_name)
        ssp_coefs_mean, ssp_coefs_std = loadtxt(populations_coeffs_file, unpack=True)

        idx_populations = ssp_coefs_mean > 0.0
        self.nBases = len(where(idx_populations)[0])
        self.range_bases = arange(self.nBases)
        self.mean_coeffs = ssp_coefs_mean[idx_populations]
        self.population_limitss = vstack((self.mean_coeffs * 0.8, self.mean_coeffs * 1.2)).T
        columns_to_delete = where(~idx_populations)

        self.obj_data['lick_idcs_df'] = read_csv(
            self.paths_dict['observations_folder'] + '{}/{}_lick_indeces.txt'.format(obj_name, obj_name),
            delim_whitespace=True, \
            header=0, index_col=0, comment='L')

        # Correction from new to old indexes
        corr_pairs = [('H1_4340A', 'H1_4341A'), ('He1_4472A', 'He1_4471A')]
        self.obj_data['lick_idcs_df'] = self.correct_df_row_name(self.obj_data['lick_idcs_df'], corr_pairs)
        self.obj_data['lick_idcs_df'] = self.correct_df_row_name(self.obj_data['lick_idcs_df'], corr_pairs)

        # Redshift limits for the object
        z_max_ssp = (ssp_lib_dict['basesWave_resam'][0] / obj_wave_resam[0]) - 1.0
        z_min_ssp = (ssp_lib_dict['basesWave_resam'][-1] / obj_wave_resam[-1]) - 1.0
        self.z_max_ssp_limit = round(z_max_ssp - 0.001, 3)
        self.z_min_ssp_limit = z_min_ssp
        print 'z_limits', z_min_ssp, z_max_ssp

        # Store the data in the object dictionary
        self.obj_data['normFlux_obs'] = normFlux_obj
        self.obj_data['obs_wave_resam'] = obj_wave_resam
        self.obj_data['obs_flux_resam'] = obj_flux_resam
        self.obj_data['obs_flux_norm'] = obj_flux_norm
        self.obj_data['int_mask'] = boolean_mask * 1
        self.obj_data['obs_flux_norm_masked'] = self.obj_data['obs_flux_norm'] * self.obj_data['int_mask']
        self.obj_data['basesWave_resam'] = ssp_lib_dict['basesWave_resam']
        self.obj_data['bases_flux_norm'] = delete(ssp_lib_dict['bases_flux_norm'], columns_to_delete, axis=0)
        self.obj_data['obs_fluxEr_norm'] = 0.05

        return

    def import_emission_line_data(self, obj_lines_df, input_ions):

        # If wavelengths are provided for the observation we use them, else we use the theoretical values
        if all(obj_lines_df.obs_wavelength.isnull().values):
            idx_obs_labels = self.lines_df.index.isin(obj_lines_df.index)
            obj_lines_df['obs_wavelength'] = self.lines_df.loc[idx_obs_labels].wavelength

        # Sort the dataframe by wavelength in case it isn't
        obj_lines_df.sort_values(by=['obs_wavelength'], ascending=True, inplace=True)

        # Get the references for the lines treatment
        idx_obj_lines               = self.lines_df.index.isin(obj_lines_df.index)
        obj_lines_df['emis_type']   = self.lines_df.loc[idx_obj_lines].emis_type.astype(str)
        obj_lines_df['pynebCode']   = self.lines_df.loc[idx_obj_lines].pyneb_code
        obj_lines_df['ion']         = self.lines_df.loc[idx_obj_lines].ion.astype(str)

        # Save the data in the dictionary according to recomb or colExt format
        # TODO Code to change if we remove recomb/colExt dividion
        # TODO add fluxes when we store synthetic data to a file

        idx_recomb = (obj_lines_df.emis_type == 'rec') & (obj_lines_df.ion.isin(input_ions))
        self.obj_data['recombLine_ions']      = obj_lines_df.loc[idx_recomb].ion.values
        self.obj_data['recombLine_labes']     = obj_lines_df.loc[idx_recomb].index.values
        self.obj_data['recombLine_waves']     = obj_lines_df.loc[idx_recomb].obs_wavelength.values
        self.obj_data['recombLine_pynebCode'] = obj_lines_df.loc[idx_recomb].pynebCode.values
        idx_col = (obj_lines_df.emis_type == 'col') & (obj_lines_df.ion.isin(input_ions))
        self.obj_data['colLine_ions']         = obj_lines_df.loc[idx_col].ion.values
        self.obj_data['colLine_labes']        = obj_lines_df.loc[idx_col].index.values
        self.obj_data['colLine_waves']        = obj_lines_df.loc[idx_col].obs_wavelength.values
        self.obj_data['colLine_pynebCode']    = obj_lines_df.loc[idx_col].pynebCode.values

        # Generate the dictionary with pyneb ions
        self.ionDict = {}
        for raw_idx in obj_lines_df.index:
            ion = obj_lines_df.loc[raw_idx].ion
            if ion not in self.ionDict:
                element, state = ion[:-1], ion[-1]
                if obj_lines_df.loc[raw_idx].emis_type == 'rec':
                    self.ionDict[ion] = RecAtom(element, state)
                elif obj_lines_df.loc[raw_idx].emis_type == 'col':
                    self.ionDict[ion] = Atom(element, state)

        # Establish index of lines which below to high and low ionization zones
        # TODO This should also include recomb (unnecesary if we  we remove recomb/colExt dividion)
        self.idx_highU = in1d(self.obj_data['colLine_ions'], self.high_temp_ions)
        self.idx_lowU = ~self.idx_highU

        # Parameters to improve calculation speed:
        self.n_recombLines, self.n_colExcLines = len(self.obj_data['recombLine_labes']), len(self.obj_data['colLine_labes'])
        self.range_recombLines, self.range_colExcLines = arange(self.n_recombLines), arange(self.n_colExcLines)

        # Empty Ionic dictionary for the MCMC
        self.abund_dict = {ion: 0 for ion in self.ionDict.keys()}

        return

    def import_emissivity_grids(self):

        # TODO This must be change to a mechanism which recognizes missing ions/grids
        # Generate recomb emissivity grids. Check if they are already available from previous run
        if path.isfile(self.paths_dict['recomb_grid']):
            self.recomb_emis_grid = load_emissivity_grid(self.paths_dict['recomb_grid'])
        else:
            self.recomb_emis_grid = generate_emissivity_grid(self.obj_data['recombLine_pynebCode'],
                                                             self.obj_data['recombLine_ions'], self.ionDict,
                                                             self.tem_grid_range, self.den_grid_range)
            # Save the grid
            save_emissivity_grid(self.paths_dict['recomb_grid'], self.recomb_emis_grid)

        # Generate coll emissivity grids. Check if they are already available from previous run
        if path.isfile(self.paths_dict['collext_grid']):
            self.metals_emis_grid = load_emissivity_grid(self.paths_dict['collext_grid'])
        else:
            self.metals_emis_grid = generate_emissivity_grid(self.obj_data['colLine_pynebCode'],
                                                             self.obj_data['colLine_ions'], self.ionDict,
                                                             self.tem_grid_range, self.den_grid_range)

            # Save the grid
            save_emissivity_grid(self.paths_dict['collext_grid'], self.metals_emis_grid)

        # Normalize the grids by Hbeta value
        self.Hbeta_emis_grid = generate_emissivity_grid([4861.0], ['H1'], self.ionDict, self.tem_grid_range, self.den_grid_range)

        self.recomb_emis_grid = self.recomb_emis_grid / self.Hbeta_emis_grid
        self.metals_emis_grid = self.metals_emis_grid / self.Hbeta_emis_grid

        return

    def load_ssp_library(self, ssp_lib_type, data_folder=None, data_file=None, wavelengh_limits=None, resample_inc=None, norm_interval=None):

        # Store stellar base type
        sspLib_dict = {'data_type': ssp_lib_type}

        # Import the base type
        if ssp_lib_type == 'FIT3D':

            # Check if more files are being introduced
            if ',' in data_file:
                ssp_lib1, ssp_lib2 = data_file.split(',')  # Corrently we are only using the first one (the big)
            else:
                ssp_lib1 = data_file

            sspLib_dict = self.import_Fit3D_ssplibrary(data_folder + ssp_lib1)

        elif ssp_lib_type == 'starlight':

            sspLib_dict = self.import_STARLIGHT_ssplibrary(data_folder, data_file)

        # Store stellar base type
        sspLib_dict['data_type'] = ssp_lib_type

        #Trim, resample and normalized the ssp library if required
        if wavelengh_limits or resample_inc or norm_interval:
            self.treat_input_spectrum(sspLib_dict, sspLib_dict['basesWave'], sspLib_dict['fluxBases'], wavelengh_limits, resample_inc, norm_interval)

        return sspLib_dict

    def treat_input_spectrum(self, output_dict, spec_wave, spec_flux, wavelengh_limits = None, resample_inc = None, norm_interval = None):

        #TODO we should remove the nBases requirement by some style which can just read the number of dimensions

        #Store input values
        output_dict['wavelengh_limits']    = wavelengh_limits
        output_dict['resample_inc']        = resample_inc
        output_dict['norm_interval']       = norm_interval

        #Resampling the spectra
        if resample_inc is not None:
            wave_resam = arange(wavelengh_limits[0], wavelengh_limits[-1], resample_inc, dtype=float)

            #Loop throught the fluxes (In the case of the bases it is assumed they may have different wavelength ranges)
            if isinstance(spec_flux, list):

                flux_resam = empty((output_dict['nBases'], len(wave_resam)))
                for i in range(output_dict['nBases']):
                    flux_resam[i, :] = interp1d(spec_wave[i], spec_flux[i], bounds_error=True)(wave_resam)

            #In case only one dimension
            elif spec_flux.ndim == 1:
                flux_resam = interp1d(spec_wave, spec_flux, bounds_error=True)(wave_resam)

            output_dict['wave_resam'] = wave_resam
            output_dict['flux_resam'] = flux_resam

        else:
            output_dict['wave_resam'] = spec_wave
            output_dict['flux_resam'] = spec_flux

        #Normalizing the spectra
        if norm_interval is not None:

            #Loop throught the fluxes (In the case of the bases it is assumed they may have different wavelength ranges)
            if isinstance(spec_flux, list):

                normFlux_coeff  = empty(output_dict['nBases'])
                flux_norm       = empty((output_dict['nBases'], len(wave_resam)))
                for i in range(output_dict['nBases']):
                    idx_Wavenorm_min, idx_Wavenorm_max = searchsorted(spec_wave[i], norm_interval)
                    normFlux_coeff[i]   = mean(spec_flux[i][idx_Wavenorm_min:idx_Wavenorm_max])
                    flux_norm[i]        = output_dict['flux_resam'][i] / normFlux_coeff[i]

            elif spec_flux.ndim == 1:
                idx_Wavenorm_min, idx_Wavenorm_max = searchsorted(spec_wave, norm_interval)
                normFlux_coeff          = mean(spec_flux[idx_Wavenorm_min:idx_Wavenorm_max])
                flux_norm               = output_dict['flux_resam'] / normFlux_coeff

            output_dict['flux_norm'] = flux_norm
            output_dict['normFlux_coeff'] = normFlux_coeff

        else:

            output_dict['flux_norm'] = output_dict['flux_resam']
            output_dict['normFlux_coeff'] = 1.0

        return

    def generate_object_mask(self):

        # TODO We need to adapt this from the lick indeces system to a mask_label wmin wmax (or viceversa)
        # TODO If not mask is included generate one from emission lines
        # TODO if not mask is applied mask = all True
        obj_mask_df = read_csv(self.obj_data['obs_mask_address'], delim_whitespace=True, header=0, index_col=0)

        boolean_mask = ones(len(self.obj_data['wave_resam']), dtype=bool)

        for mask_label in obj_mask_df.index:
            wmin, wmax = obj_mask_df.loc[mask_label, 'wmin'], obj_mask_df.loc[mask_label, 'wmax']
            idx_cur_spec_mask = (self.obj_data['wave_resam'] > wmin) & (self.obj_data['wave_resam'] < wmax)
            boolean_mask = boolean_mask & ~idx_cur_spec_mask

        self.obj_data['boolean_mask'] = boolean_mask
        self.obj_data['int_mask']     = boolean_mask * 1

        self.obj_data['flux_norm_mask'] = self.obj_data['flux_norm'] * self.obj_data['int_mask']

        return

class ContinuaComponents(ssp_fitter, NebularContinuumCalculator):

    def __init__(self):

        #Load tools for continua calculation
        ssp_fitter.__init__(self)
        NebularContinuumCalculator.__init__(self)

    def nebular_Cont(self, wave_obs, z, cHbeta, Te, He1_abund, He2_abund, Halpha_Flux):

        wave_obs_rest   = wave_obs / (1.0 + z)

        neb_gCont       = self.calculate_neb_gCont(wave_obs_rest, Te, He1_abund, He2_abund)

        neb_int_norm    = self.gCont_calibration(wave_obs_rest, Te, Halpha_Flux, neb_gCont)

        neb_xX          = self.reddening_Xx(wave_obs_rest, 'G03_average', 3.4)
        flambda_neb     = neb_xX/self.Hbeta_xX - 1.0

        neb_flux_norm   = neb_int_norm * power(10, -1 * flambda_neb * cHbeta)

        return neb_flux_norm

    def calculate_nebular_SED(self, wave_obs, z, cHbeta, Te, He1_abund, He2_abund, Halpha_Flux):

        wave_obs_rest   = wave_obs / (1.0 + z)

        neb_gCont       = self.calculate_neb_gCont(wave_obs_rest, Te, He1_abund, He2_abund)

        neb_int_norm    = self.gCont_calibration(wave_obs_rest, Te, Halpha_Flux, neb_gCont)

        neb_xX          = self.reddening_Xx(wave_obs_rest, 'G03_average', 3.4) #TODO Change by global gas reddening law
        flambda_neb     = neb_xX/self.Hbeta_xX - 1.0

        neb_flux_norm   = neb_int_norm * power(10, -1 * flambda_neb * cHbeta)

        nebular_SED = {'neb_gCont': neb_gCont, 'neb_int_norm': neb_int_norm, 'neb_xX': neb_xX,
                       'flambda_neb': flambda_neb, 'neb_flux_norm': neb_flux_norm}

        return nebular_SED

class EmissionComponents(LineMesurer_v2):

    def __init__(self):

        #Load tools to measure lines
        LineMesurer_v2.__init__(self,  self.paths_dict['dazer_path'] + 'format/', 'DZT_LineLog_Headers.dz')

        #Hbeta configuration
        self.Hbeta_label            = 'H1_4861A'
        self.Hbeta_wave             = 4862.683
        self.Hbeta_pynebCode        = '4_2'

        #Import Optical depth function
        posHelium_Lines             = ['He1_3889A',  'He1_4026A',  'He1_4387A',    'He1_4471A',    'He1_4686A',    'He1_4714A',    'He1_4922A',   'He1_5876A',    'He1_6678A',   'He1_7065A',    'He1_7281A',    'He1_10830A']
        self.Coef_ftau_dict         = self.import_optical_depth_coeff_table(posHelium_Lines)

    def OpticalDepth_He(self, tau, T_4, ne, He_label):

        f_tau   = 1 + (tau/2) * (self.Coef_ftau_dict[He_label][0] + (self.Coef_ftau_dict[He_label][1] + self.Coef_ftau_dict[He_label][2]*ne + self.Coef_ftau_dict[He_label][3]*ne*ne) * T_4)

        return f_tau

    def calculate_recomb_fluxes(self, Thigh, ne, cHbeta, tau, lines_abund_dict, lines_labels, lines_ions, lines_flambda):

        #Emissivity for the two temperature layers
        t4 = Thigh / 10000.0

        #Interpolate the emissivities
        emis_module = bilinear_interpolator_axis(ne, Thigh, self.den_grid_range, self.tem_grid_range, self.recomb_emis_grid)

        #Loop throught the lines to generate the f_tau correction
        lines_ftau_vector = empty(self.n_recombLines)
        lines_abund_vector = empty(self.n_recombLines)

        for i in self.range_recombLines:
            if lines_ions[i] == 'He1':
                lines_ftau_vector[i]    = self.OpticalDepth_He(tau = tau, T_4 = t4, ne = ne, He_label = lines_labels[i])
            else:
                lines_ftau_vector[i]    = 1.0
            lines_abund_vector[i] = lines_abund_dict[lines_ions[i]]

        #Reddening factor for all the lines
        f_module = power(10, -1 * lines_flambda * cHbeta)

        #Metals flux
        recomb_fluxes = lines_abund_vector * emis_module * lines_ftau_vector * f_module

        return recomb_fluxes

    def calculate_colExcit_flux(self, Tlow, Thigh, ne, cHbeta, lines_abund_dict, lines_waves, lines_ions, lines_flambda):

        # Array to store the emissivities
        lines_emis_vector = empty(self.n_colExcLines)

        #Calculate low ionization emissivities
        lines_emis_vector[self.idx_lowU] = bilinear_interpolator_axis(ne, Tlow, self.den_grid_range,
                                                                      self.tem_grid_range,
                                                                      self.metals_emis_grid[:, :, self.idx_lowU])

        #Calculate high ionization emissivities
        lines_emis_vector[self.idx_highU] = bilinear_interpolator_axis(ne, Thigh, self.den_grid_range,
                                                                       self.tem_grid_range,
                                                                      self.metals_emis_grid[:, :, self.idx_highU])

        # Loop through the lines to assign the ionic abundances
        abund_vector = empty(self.n_colExcLines)
        for i in self.range_colExcLines:
            ion = lines_ions[i]
            abund_vector[i] = lines_abund_dict[ion]

        # Reddening factor for all the lines
        f_module = power(10, -1 * lines_flambda * cHbeta)

        # Metals flux
        colExcit_fluxes = abund_vector * lines_emis_vector * f_module

        return colExcit_fluxes

    def reddening_parameters(self):

        # TODO a class should be created to include reddening features for the function
        # Hbeta parameters #TODO This could go into the configuration file (change the normalizing wavelength?)
        self.Hbeta_xX   = self.reddening_Xx(array([self.Hbeta_wave]), self.reddedning_curve_model, self.Rv_model)[0]

        recomblines_xX  = self.reddening_Xx(self.obj_data['recombLine_waves'], self.reddedning_curve_model, self.Rv_model)
        colLines_xX     = self.reddening_Xx(self.obj_data['colLine_waves'], self.reddedning_curve_model, self.Rv_model)

        self.obj_data['recombLine_flambda'] = recomblines_xX / self.Hbeta_xX - 1.0
        self.obj_data['colLine_flambda'] = colLines_xX / self.Hbeta_xX - 1.0

        return

class SpectrumFitter(Import_model_data, ContinuaComponents, EmissionComponents, ReddeningLaws, Plot_Conf):

    def __init__(self):

        #Import tools to load data
        Import_model_data.__init__(self)
        ContinuaComponents.__init__(self)
        EmissionComponents.__init__(self)

        #Import sub classes
        ReddeningLaws.__init__(self)

        #For generating graphs
        Plot_Conf.__init__(self)

    def calc_emis_spectrum(self, wavelength_range, lines_waves, lines_fluxes, lines_mu, lines_sigma, redshift):

        #TODO This should go into the cinematics class

        lines_mu = lines_mu * (1 + redshift)

        A_lines = lines_fluxes / (lines_sigma * self.sqrt2pi)

        wave_matrix = wavelength_range * ones((lines_waves.shape[0], wavelength_range.shape[0]))

        emis_spec_matrix = A_lines[:, None] * exp(-(wave_matrix - lines_mu[:, None]) * (wave_matrix - lines_mu[:, None]) / (2 * lines_sigma * lines_sigma))

        combined_spectrum = emis_spec_matrix.sum(axis=0)

        return combined_spectrum

    def gen_synth_obs(self, spectra_components = None, input_ions = None,
                      wavelengh_limits = None, resample_inc = None, norm_interval = None,
                      obj_properties_file = None, obj_lines_file = None, obj_mask_file = None, output_folder = None,
                      ssp_lib_type = None, data_folder = None, data_file = None ,obj_ssp_coeffs_file = None,
                      error_stellarContinuum = None, error_recomb_lines = None, error_collexc_lines = None):

        # TODO we will need to change to recomb scheme: He1r hence, ion_dict = pn.getAtomDict(atom_list = atoms_list)
        # Dictionary to store the data
        self.obj_data = {}

        # Store input files:
        self.obj_data['obj_properties_file']   = obj_properties_file
        self.obj_data['obj_lines_file']        = obj_lines_file
        self.obj_data['obj_ssp_coeffs_file']   = obj_ssp_coeffs_file
        self.obj_data['obs_mask_address']      = obj_mask_file
        self.obj_data['output_folder']         = output_folder

        # Read simulation data from file
        obj_prop_df = read_csv(obj_properties_file, delim_whitespace=True, header=0, index_col=0)

        #--------Lines calculation
        if 'emission' in spectra_components:

            #Store input data
            self.obj_data['flux_hbeta'] = obj_prop_df.loc['flux_hbeta'][0]

            #Read lines file
            obj_lines_df = read_csv(obj_lines_file, delim_whitespace=True, header=0, index_col=0)

            # Prepare data from emission line file
            self.import_emission_line_data(obj_lines_df, input_ions)

            # Create or load emissivity grids
            self.import_emissivity_grids()

            # Reddening parameters
            self.reddening_parameters()

            #Dictionary with synthetic abundances
            abund_df        = obj_prop_df[obj_prop_df.index.str.contains('_abund')]
            abund_keys      = abund_df.index.str.rstrip('_abund').astype(str).values
            abund_values    = abund_df.variable_magnitude.values
            self.abund_dict = dict(zip(abund_keys, abund_values.T))

            #Calculate T_high assuming we get T_low
            self.obj_data['T_low']  = obj_prop_df.loc['T_low'][0]
            self.obj_data['T_high'] = (1.0807 * self.obj_data['T_low'] / 10000.0 - 0.0846) * 10000.0

            # Prepare the lines data
            self.obj_data['recomb_fluxes'] = self.calculate_recomb_fluxes(self.obj_data['T_high'], obj_prop_df.loc['n_e'][0],
                                                            obj_prop_df.loc['cHbeta'][0], obj_prop_df.loc['tau'][0],
                                                            self.abund_dict,
                                                            self.obj_data['recombLine_labes'],
                                                            self.obj_data['recombLine_ions'],
                                                            self.obj_data['recombLine_flambda'])

            self.obj_data['metal_fluxes'] = self.calculate_colExcit_flux(self.obj_data['T_low'], self.obj_data['T_high'],
                                                                obj_prop_df.loc['n_e'][0], obj_prop_df.loc['cHbeta'][0],
                                                                self.abund_dict,
                                                                self.obj_data['colLine_waves'],
                                                                self.obj_data['colLine_ions'],
                                                                self.obj_data['colLine_flambda'])

            #Use general error if this is provided
            if error_recomb_lines is not None:
                self.obj_data['recomb_err']= self.obj_data['recomb_fluxes'] * error_recomb_lines
            if error_collexc_lines is not None:
                self.obj_data['metal_err'] = self.obj_data['metal_fluxes'] * error_collexc_lines

        #--------Nebular calculation
        if 'nebular' in spectra_components:

            #Save input conditions:
            self.obj_data['wavelengh_limits']  = wavelengh_limits
            self.obj_data['resample_inc']      = resample_inc
            self.obj_data['norm_interval']     = norm_interval
            self.obj_data['z_star']            = obj_prop_df.loc['z_star'][0]

            # Rest stellar and observed wavelength
            obj_wave_rest = arange(wavelengh_limits[0], wavelengh_limits[-1], resample_inc, dtype=float)
            obj_wave_obs = obj_wave_rest * (1.0 + self.obj_data['z_star']) # TODO we should change this to z_obj

            #Get Halpha flux to calibrate
            idx_Halpha = (self.obj_data['recombLine_labes'] == 'H1_6563A')
            self.obj_data['flux_halpha'] = self.obj_data['recomb_fluxes'][idx_Halpha] * obj_prop_df.loc['flux_hbeta'][0] #/ self.stellar_SED['normFlux_stellar']

            #Calculate the nebular continua
            self.obj_data['neb_SED'] = self.calculate_nebular_SED(obj_wave_rest, # TODO We must change this to the function used on the final code
                                                     obj_prop_df.loc['z_star'][0],
                                                     obj_prop_df.loc['cHbeta'][0],
                                                     obj_prop_df.loc['T_low'][0],
                                                     obj_prop_df.loc['He1_abund'][0],
                                                     obj_prop_df.loc['He2_abund'][0],
                                                    self.obj_data['flux_halpha'])

            self.obj_data['obs_wave_rest'] = obj_wave_rest
            self.obj_data['obs_wave']      = obj_wave_obs
            self.obj_data['obs_flux']      = self.obj_data['neb_SED']['neb_int_norm']

        #--------Stellar calculation
        if 'stellar' in spectra_components:

            # Save input conditions:
            self.obj_data['wavelengh_limits']  = wavelengh_limits
            self.obj_data['resample_inc']      = resample_inc
            self.obj_data['norm_interval']     = norm_interval
            self.obj_data['z_star']            = obj_prop_df.loc['z_star'][0]
            self.obj_data['Av_star']           = obj_prop_df.loc['Av_star'][0]
            self.obj_data['sigma_star']        = obj_prop_df.loc['sigma_star'][0]
            self.obj_data['flux_hbeta']        = obj_prop_df.loc['flux_hbeta'][0]
            self.obj_data['eqw_hbeta']         = obj_prop_df.loc['eqw_hbeta'][0]

            # Import the stellar library
            self.ssp_lib = self.load_ssp_library(ssp_lib_type, data_folder, data_file, wavelengh_limits, resample_inc, norm_interval)

            # Trim bases flux to include only the stellar spectra contributing in our object
            zeros_array = ones(10)
            self.prepare_ssp_data(self.obj_data['obj_ssp_coeffs_file'], obj_wave = ones(10), obj_flux = ones(10),
                                  obj_flux_err = ones(10), obj_mask = ones(10))

            # Rest stellar and observed wavelength
            obj_wave_rest = arange(wavelengh_limits[0], wavelengh_limits[-1], resample_inc, dtype=float)
            obj_wave_obs = obj_wave_rest * (1.0 + self.obj_data['z_star'])

            # SSP library flux at modelled Av, z_star and sigma_star
            ssp_grid_model_norm = self.physical_SED_model(self.ssp_lib['wave_resam'], obj_wave_obs, self.onBasesFluxNorm,
                                    self.obj_data['Av_star'], self.obj_data['z_star'], self.obj_data['sigma_star'], Rv_coeff=self.Rv_model)

            #Normalized object flux
            obj_flux_norm = ssp_grid_model_norm.dot(self.sspPrefit_Coeffs)

            #Instead of denormalizing the grid we use the Hbeta flux and equivalent width
            #To get a better shape of the nebular and stellar continua
            cont_hbeta  = self.obj_data['flux_hbeta'] / self.obj_data['eqw_hbeta']
            obj_flux = obj_flux_norm * cont_hbeta

            # Generate synth error
            sigma_err   = error_stellarContinuum * median(obj_flux) # TODO We should play with this error
            stellar_err = random.normal(0.0, sigma_err, len(obj_flux_norm))

            # Store the data vector
            self.obj_data['obs_wave_rest']         = obj_wave_rest
            self.obj_data['obs_wave']              = obj_wave_obs
            self.obj_data['stellar_flux']          = obj_flux
            self.obj_data['stellar_flux_err']      = obj_flux + stellar_err
            self.obj_data['sigma_continuum']       = 0.02   #TODO put this in the object data

            #Save synthetic continua according to the observations
            if 'obs_flux' not in self.obj_data:
                self.obj_data['obs_flux'] = self.obj_data['stellar_flux_err']
            else:
                self.obj_data['obs_flux'] = self.obj_data['obs_flux'] + self.obj_data['stellar_flux_err']

        return self.obj_data.copy()


    def ready_simulation(self, model_name, output_folder, obs_data, ssp_data, fitting_components, overwrite_grids=False,
                         input_ions=None, wavelengh_limits = None, resample_inc=None, norm_interval=None):

        # Dictionary to store the data
        self.obj_data = obs_data.copy()

        if output_folder is None: # TODO need to establish a global path to save the data
            self.output_folder = self.obj_data['output_folder']

        # Prepare emission data
        if 'emission' in fitting_components:

            obj_lines_df = read_csv(obs_data['obj_lines_file'], delim_whitespace=True, header=0, index_col=0)

            #Prepare data from emission line file
            self.import_emission_line_data(obj_lines_df, input_ions)

            #Create or load emissivity grids
            self.import_emissivity_grids()

            # Reddening parameters
            self.reddening_parameters()

        # Prepare stellar data
        if 'stellar' in fitting_components:

            # Create dictionary with the stellar library configuration which this object will use
            self.ssp_lib = ssp_data.copy()

            # Trim, resample and normalize according to the input object
            self.treat_input_spectrum(self.obj_data, self.obj_data['obs_wave'], self.obj_data['obs_flux'], wavelengh_limits,
                                      resample_inc, norm_interval)

            # Generate object masks:
            self.generate_object_mask()

        return

    def prepare_ssp_data(self, input_data, obj_wave, obj_flux, obj_flux_err, obj_mask):

        #Case of a prefit run
        if input_data is None:

            #Default parameters for the nebular continuum
            Te_neb, z_neb, cHbeta_neb = self.conf_dic['Te_neb'], self.conf_dic['z_neb'], self.conf_dic['cHbeta_neb']
            He1_neb, He2_neb = self.conf_dic['He1_neb'], self.conf_dic['He2_neb']

            #Generate synthetic nebular emission to remove from object
            self.obj_data['synth_neb_flux'] = self.nebular_Cont(obj_wave, z_neb, cHbeta_neb, Te_neb,
                                            He1_neb, He2_neb, self.obj_data['flux_halpha'] / self.obj_data['normFlux_coeff'])

            object_continuum = (obj_flux - self.obj_data['synth_neb_flux']) * obj_mask

            idx_populations = ones(self.ssp_lib['flux_resam'].shape[0], dtype=bool)

        else:

            bases_idx, bases_coeff = loadtxt(input_data, usecols=[0, 1], unpack=True)

            idx_populations = bases_coeff >= self.lowlimit_sspContribution # TODO we should check this limit thing currentl it must be 0.001

            object_continuum = obj_flux * obj_mask

            self.sspPrefit_Idcs = where(idx_populations)[0]
            self.sspPrefit_Coeffs = bases_coeff[idx_populations]
            self.sspPrefit_Limits = vstack((self.sspPrefit_Coeffs * 0.8, self.sspPrefit_Coeffs * 1.2)).T

        #Object data
        self.input_continuum        = object_continuum
        self.input_continuum_er     = obj_flux_err
        self.input_wave             = obj_wave
        self.int_mask               = obj_mask

        #Bases parameters
        neglected_populations       = where(~idx_populations)
        self.onBasesWave            = self.ssp_lib['wave_resam']
        self.onBasesFlux            = delete(self.ssp_lib['flux_resam'], neglected_populations, axis=0)
        self.onBasesFluxNorm        = delete(self.ssp_lib['flux_norm'], neglected_populations, axis=0)
        self.onBasesFluxNormCoeffs  = delete(self.ssp_lib['normFlux_coeff'], neglected_populations, axis=0)
        self.range_bases            = arange(self.onBasesFlux.shape[0])

        # Limit for bases
        z_max_ssp                   = (self.ssp_lib['wave_resam'][0] / obj_wave[0]) - 1.0
        z_min_ssp                   = (self.ssp_lib['wave_resam'][-1] / obj_wave[-1]) - 1.0
        self.zMin_SspLimit          = z_min_ssp
        self.zMax_SspLimit          = round(z_max_ssp - 0.001, 3)

        return

    def save_prefit_data(self):

        #-- Save
        # Read input data #TODO are an extension/code/folder for each run
        stellarPrefit_db, stat_db_dict = self.load_pymc_database_manual(self.prefit_db, burning=1000, params_list=['Av_star', 'sigma_star', 'ssp_coefficients'])

        # Save population coefficients
        sspCoeffs_file = self.input_folder + 'prefit_populations.txt'  # TODO Default files names should go into the configuration
        coeffs_vector = stat_db_dict['ssp_coefficients']['trace'].mean(axis=0)
        pops_vector = arange(len(coeffs_vector), dtype=int)
        savetxt(sspCoeffs_file, transpose(array([pops_vector, coeffs_vector])), fmt="%4i %10.8f")

        # Store prefit data
        self.ssp_lib['db_sspPrefit']        = stellarPrefit_db
        self.ssp_lib['dbDict_sspPrefit']    = stat_db_dict
        self.ssp_lib['Av_sspPrefit']        = stat_db_dict['Av_star']['mean']
        self.ssp_lib['sigma_sspPrefit']     = stat_db_dict['sigma_star']['mean']

    def load_prefit_data(self, obj_wave):

        #-----Observation versus prefit comparison
        stellarPrefit_db, stat_db_dict      = self.load_pymc_database_manual(self.prefit_db, burning=300,
                                              params_list=['Av_star', 'sigma_star', 'ssp_coefficients'])

        self.ssp_lib['Av_sspPrefit']        = stat_db_dict['Av_star']['mean']
        self.ssp_lib['sigma_sspPrefit']     = stat_db_dict['sigma_star']['mean']

        # Default parameters for the nebular continuum
        Te_neb, z_neb, cHbeta_neb           = self.conf_dic['Te_neb'], self.conf_dic['z_neb'], self.conf_dic['cHbeta_neb']
        He1_neb, He2_neb                    = self.conf_dic['He1_neb'], self.conf_dic['He2_neb']

        # Generate synthetic nebular emission to remove from object
        self.ssp_lib['synth_neb_flux']      = self.nebular_Cont(obj_wave, z_neb, cHbeta_neb, Te_neb, He1_neb, He2_neb,
                                                    self.obj_data['flux_halpha'] / self.obj_data['normFlux_coeff'])

        return

    def plot_input_data(self):

        self.FigConf()

        #----- Prefit comparison
        # TODO this calculation should not be here... we should be able to change it to prepare_data or somewhere else
        ssp_grid_i_norm = self.physical_SED_model(self.ssp_lib['wave_resam'], self.obj_data['wave_resam'],self.onBasesFluxNorm,
                                                  self.ssp_lib['Av_sspPrefit'], 0.0, self.ssp_lib['sigma_sspPrefit'], self.Rv_model)
        obj_ssp_fit_flux = ssp_grid_i_norm.dot(self.sspPrefit_Coeffs)

        self.data_plot(self.input_wave, self.obj_data['flux_norm'], 'Object normed flux')
        self.data_plot(self.input_wave, self.obj_data['synth_neb_flux'], 'Nebular continuum')
        self.data_plot(self.input_wave, obj_ssp_fit_flux + self.obj_data['synth_neb_flux'], 'Prefit continuum output', linestyle=':')

        self.FigWording(xlabel='Wavelength $(\AA)$', ylabel='Observed flux', title='SSPs continuum prefit')
        self.savefig(self.input_folder + 'ssp_prefit', resolution=200)

        # #-----Prefit SSPs norm plot
        #TODO This function should go to my collection
        ordinal_generator = lambda n: "%d%s" % (n, "tsnrhtdd"[(n / 10 % 10 != 1) * (n % 10 < 4) * n % 10::4])
        ordinal_bases = [ordinal_generator(n) for n in self.sspPrefit_Idcs]

        for i in range(len(self.onBasesFluxNorm)):
            if self.sspPrefit_Coeffs[i] > 0.01:
                label_i = '{} base: flux coeff {}, norm coeff {:.2E}'.format(ordinal_bases[i], self.sspPrefit_Coeffs[i], self.onBasesFluxNormCoeffs[i])
                self.data_plot(self.onBasesWave, self.onBasesFluxNorm[i], label_i)
        self.area_fill(self.ssp_lib['norm_interval'][0], self.ssp_lib['norm_interval'][1], 'Norm interval: {} - {}'.format(self.ssp_lib['norm_interval'][0], self.ssp_lib['norm_interval'][1]), alpha=0.5)

        self.FigWording(xlabel='Wavelength $(\AA)$', ylabel = 'Normalized flux', title = 'SSP prefit contributing stellar populations')
        self.savefig(self.input_folder + 'prefit_NormSsps', resolution=200)

        # #-----Plot input data
        self.data_plot(self.input_wave, self.input_continuum, 'Object Input continuum')
        self.data_plot(self.obj_data['obs_wave'], self.obj_data['synth_neb_flux'], 'synth_neb_flux', linestyle = '--')
        self.data_plot(self.input_wave, obj_ssp_fit_flux , 'Stellar Prefit continuum output', linestyle=':')

        #In case of a synthetic observation:
        if 'neb_SED' in self.obj_data:
            self.data_plot(self.input_wave, self.obj_data['neb_SED']['neb_int_norm'], 'Nebular continuum')
            title_label = 'Observed spectrum'
        if 'stellar_flux' in self.obj_data:
            self.data_plot(self.obj_data['obs_wave'], self.obj_data['stellar_flux']/self.obj_data['normFlux_coeff'], 'Stellar continuum')
            self.data_plot(self.obj_data['obs_wave'], self.obj_data['stellar_flux_err']/ self.obj_data['normFlux_coeff'], 'Stellar continuum with uncertainty', linestyle=':')
            title_label = 'Synthetic spectrum'

        self.FigWording(xlabel='Wavelength $(\AA)$', ylabel = 'Observed flux', title = title_label)
        self.savefig(self.input_folder + 'prefit_components', resolution=200)

        # #-----Plot masked spectrum
        self.data_plot(self.obj_data['obs_wave'], self.obj_data['flux_norm'], 'Normalized observation')
        self.data_plot(self.input_wave, self.input_continuum, 'Masked observation', linestyle='--')
        self.FigWording(xlabel='Wavelength $(\AA)$', ylabel = 'Observed flux', title = 'Spectrum masks')
        self.savefig(self.input_folder + 'spectrum_mask', resolution=200)

        # #-----Resampled observation
        self.data_plot(self.obj_data['obs_wave'], self.obj_data['obs_flux'], 'Observed spectrum')
        self.data_plot(self.obj_data['wave_resam'], self.obj_data['flux_resam'], 'Resampled spectrum', linestyle='--')
        self.data_plot(self.obj_data['wave_resam'], self.obj_data['flux_norm'] * self.obj_data['normFlux_coeff'], r'Normalized spectrum $\cdot$ {:.2E}'.format(self.obj_data['normFlux_coeff']), linestyle=':')
        self.area_fill(self.obj_data['norm_interval'][0], self.obj_data['norm_interval'][1], 'Norm interval: {} - {}'.format(self.obj_data['norm_interval'][0], self.obj_data['norm_interval'][1]), alpha=0.5)
        self.FigWording(xlabel='Wavelength $(\AA)$', ylabel = 'Observed flux', title = 'Resampled observation')
        self.savefig(self.input_folder + 'resampled_spectra', resolution=200)

        # Stellar prefit Traces
        self.traces_plot(['Av_star', 'sigma_star'], self.ssp_lib['db_sspPrefit'], self.ssp_lib['dbDict_sspPrefit'])
        self.save_manager(self.input_folder + 'PrefitTracesPlot', save=True, save_pickle=False)

        # Stellar prefit Posteriors
        self.posteriors_plot(['Av_star', 'sigma_star'], self.ssp_lib['db_sspPrefit'], self.ssp_lib['dbDict_sspPrefit'])
        self.save_manager(self.input_folder + 'PrefitPosteriorPlot', save=True, save_pickle=False)


        return

class SpecSynthesizer(SpectrumFitter):

    def __init__(self, atomic_ref=None, nebular_data = None, ssp_type=None, ssp_folder=None, ssp_conf_file=None,
                 temp_grid=None, den_grid=None, high_temp_ions=None, R_v=3.4, reddenig_curve='G03_average', lowlimit_sspContribution=0.0):

        #TODO in here we give the choice: Configuration from text file but it can also be imported from text file create a default conf to upload from there if missing

        # Import parent classes
        SpectrumFitter.__init__(self)

        # Load nebular constants data
        if nebular_data is None:
            self.load_neb_constants(self.paths_dict['nebular_data_folder'])

        # Define atomic data:
        if atomic_ref == 'default':
            atomicData.setDataFile('s_iii_coll_HRS12.dat') #TODO actually this should be uplodaded from a file

        # Temperature and density grid declaration
        self.tem_grid_range = arange(temp_grid[0], temp_grid[1], temp_grid[2])
        self.den_grid_range = arange(den_grid[0], den_grid[1], den_grid[2])
        self.den_grid_range[0] = 1 #Change the minimum value for the grid to 1

        # Reddening parameters
        self.Rv_model = R_v
        self.reddedning_curve_model = reddenig_curve

        # Declare high ionization temperature ions
        self.high_temp_ions = high_temp_ions

        # Lower accepted limit for ssps
        self.lowlimit_sspContribution = lowlimit_sspContribution

        # Dictionary to store parameters
        self.conf_dic = {'Te_neb': 10000.0, 'z_neb': 0.0, 'cHbeta_neb': 0.1, 'He1_neb': 0.085, 'He2_neb': 0.0}

    def fit_observation(self, model_name, obs_data, ssp_data, iterations=15000, burn=7000, thin=1, output_folder = None,
                        fitting_components=None, input_ions=None, params_list = None, prefit_SSP = True,
                        wavelengh_limits = None, resample_inc = None, norm_interval=None):

        #Prepare data for the MCMC fitting
        self.ready_simulation(model_name, output_folder, obs_data, ssp_data, fitting_components, input_ions=input_ions,
                              wavelengh_limits=wavelengh_limits, resample_inc=resample_inc, norm_interval=norm_interval)

        #Folders to store inputs and outputs
        self.input_folder = output_folder + 'input_data/'
        self.output_folder = output_folder + 'output_data/'
        make_folder(self.input_folder)
        make_folder(self.output_folder)

        #Prefit stellar continua
        if ('stellar' in fitting_components) and prefit_SSP:

            # Ready data for a prefit on our stellar continua
            self.prepare_ssp_data(None, obj_wave=self.obj_data['wave_resam'], obj_flux=self.obj_data['flux_norm'],
                                  obj_flux_err=self.obj_data['sigma_continuum'], obj_mask=self.obj_data['int_mask'])

            # Select model
            self.select_inference_model('stelar_prefit')

            # Run prefit output #TODO these prefit parameters should go into the master conf
            self.prefit_db = self.input_folder + 'SSP_prefit_database'
            self.run_pymc2(self.prefit_db, iterations = 10000, variables_list = ['Av_star', 'sigma_star'], prefit = True)

            # Save prefit data
            self.save_prefit_data()

        #Load prefit data
        self.load_prefit_data(self.obj_data['wave_resam'])

        #Ready data for full run
        self.prepare_ssp_data(self.input_folder + 'prefit_populations.txt',
                              obj_wave=self.obj_data['wave_resam'], obj_flux=self.obj_data['flux_norm'],
                              obj_flux_err=self.obj_data['sigma_continuum'], obj_mask=self.obj_data['int_mask'])

        #Plot input simulation data
        self.plot_input_data()



        # #Select model
        # self.select_inference_model()
        #
        # #Run model
        # self.run_pymc2(self.output_folder + model_name, iterations=iterations, variables_list=variables_list, prefit=True)
        #
        # #Plot output data

        return

    def select_inference_model(self, model = 'complete'):

        if model == 'complete':
            self.inf_dict = self.complete_model()

        elif model == 'stelar_prefit':
            print 'Limites', self.zMin_SspLimit, self.zMax_SspLimit
            self.inf_dict = self.stellarContinua_model()

    def stellarContinua_model(self):

        #Stellar parameters
        Av_star     = pymc2.Uniform('Av_star', 0.0, 5.00)
        sigma_star  = pymc2.Uniform('sigma_star', 0.0, 5.00)
        #z_star      = pymc2.Uniform('z_star', self.z_min_ssp_limit, self.z_max_ssp_limit)

        @pymc2.deterministic #Shift, multiply and convolve by a factor given by the model parameters
        def ssp_coefficients(z_star=0.0, Av_star=Av_star, sigma_star=sigma_star, input_flux=self.input_continuum):

            ssp_grid_i = self.physical_SED_model(self.onBasesWave, self.input_wave, self.onBasesFluxNorm, Av_star, z_star, sigma_star, self.Rv_model)

            self.ssp_grid_i_masked = (self.int_mask * ssp_grid_i.T).T

            ssp_coeffs_norm = self.ssp_fitting(self.ssp_grid_i_masked, input_flux)

            return ssp_coeffs_norm

        @pymc2.deterministic #Theoretical normalized flux
        def stellar_continua_calculation(ssp_coeffs=ssp_coefficients):

            flux_sspFit_norm = np_sum(ssp_coeffs.T * self.ssp_grid_i_masked, axis=1)

            return flux_sspFit_norm

        @pymc2.stochastic(observed=True) #Likelihood
        def likelihood_ssp(value = self.input_continuum, stellarTheoFlux=stellar_continua_calculation, sigmaContinuum=self.input_continuum_er):
            chi_F = sum(square(stellarTheoFlux - value) / square(sigmaContinuum))
            return - chi_F / 2

        return locals()

    def complete_model(self):

        ne = pymc2.TruncatedNormal('ne', self.obj_data['nSII'], self.obj_data['nSII_error'] ** -2, a=50.0, b=1000.0)
        cHbeta = pymc2.TruncatedNormal('cHbeta', 0.15, 0.05 ** -2, a=0.0, b=3.0)
        T_low = pymc2.TruncatedNormal('T_low', self.obj_data['TSIII'], self.obj_data['TSIII_error'] ** -2, a=7000.0,
                                      b=20000.0)

        S2_abund = pymc2.Uniform('S2_abund', 0.000001, 0.001)
        S3_abund = pymc2.Uniform('S3_abund', 0.000001, 0.001)
        O2_abund = pymc2.Uniform('O2_abund', 0.000001, 0.001)
        O3_abund = pymc2.Uniform('O3_abund', 0.000001, 0.001)
        N2_abund = pymc2.Uniform('N2_abund', 0.000001, 0.001)
        Ar3_abund = pymc2.Uniform('Ar3_abund', 0.000001, 0.001)
        Ar4_abund = pymc2.Uniform('Ar4_abund', 0.000001, 0.001)

        He1_abund = pymc2.Uniform('He1_abund', 0.050, 0.15)
        tau = pymc2.TruncatedNormal('tau', 0.75, 0.5 ** -2, a=0.0, b=7.0)
        cHbeta = pymc2.TruncatedNormal('cHbeta', 0.15, 0.05 ** -2, a=0.0, b=3.0)
        #xi = pymc2.TruncatedNormal('xi', 1, 200 ** -2, a=0.0, b=1000.0)
        T_He = pymc2.TruncatedNormal('T_He', self.obj_data['TSIII'], self.obj_data['TSIII_error'] ** -2, a=7000.0,
                                     b=20000.0, value=14500.0)

        # z_star     =   pymc2.Uniform(          'z_star',       self.z_min_ssp_limit,       self.z_max_ssp_limit)
        Av_star = pymc2.Uniform('Av_star', 0.0, 5.00)
        sigma_star = pymc2.Uniform('sigma_star', 0.0, 5.00)
        ssp_coefs = [pymc2.Uniform('ssp_coefs_%i' % i, self.population_limitss[i][0], self.population_limitss[i][1]) for
                     i in self.range_bases]

        @pymc2.deterministic()
        def calc_Thigh(Te=T_low):
            return (1.0807 * Te / 10000.0 - 0.0846) * 10000.0

        @pymc2.deterministic()
        def calc_abund_dict(He1_abund=He1_abund, S2_abund=S2_abund, S3_abund=S3_abund, O2_abund=O2_abund, O3_abund=O3_abund, N2_abund=N2_abund, Ar3_abund=Ar3_abund, Ar4_abund=Ar4_abund):
            self.abund_iter_dict['He1'] = He1_abund
            self.abund_iter_dict['S2'] = S2_abund
            self.abund_iter_dict['S3'] = S3_abund
            self.abund_iter_dict['O2'] = O2_abund
            self.abund_iter_dict['O3'] = O3_abund
            self.abund_iter_dict['N2'] = N2_abund
            self.abund_iter_dict['Ar3'] = Ar3_abund
            self.abund_iter_dict['Ar4'] = Ar4_abund

            return self.abund_iter_dict

        @pymc2.deterministic
        def calc_colExcit_fluxes(abund_dict=calc_abund_dict, T_low=T_low, T_High=calc_Thigh, ne=ne, cHbeta=cHbeta):
            colExcit_fluxes = self.calculate_colExcit_flux(T_low, T_High, ne, cHbeta, abund_dict,
                                                           self.obj_data['colLine_waves'],
                                                           self.obj_data['colLine_ions'],
                                                           self.obj_data['colLine_flambda'])

            return colExcit_fluxes

        @pymc2.deterministic
        def calc_nebular_cont(z_star=self.obj_data['z_star'], cHbeta=self.obj_data['cHbeta'], Te=self.obj_data['T_low'], He1_abund=He1_abund, He2_abund=0.0, Halpha_Flux=self.Halpha_norm):
            neb_flux_norm = self.nebular_Cont(self.obj_data['obs_wave_resam'], z_star, cHbeta, Te, He1_abund, He2_abund, Halpha_Flux)

            return neb_flux_norm

        @pymc2.deterministic
        def calc_continuum(z_star=self.obj_data['z_star'], Av_star=Av_star, sigma_star=sigma_star, ssp_coefs=ssp_coefs, nebular_flux=calc_nebular_cont):
            ssp_grid_i = self.physical_SED_model(self.obj_data['basesWave_resam'], self.obj_data['obs_wave_resam'],
                                                 self.obj_data['bases_flux_norm'], \
                                                 Av_star, z_star, sigma_star, 3.4)

            fit_continuum = ssp_grid_i.dot(ssp_coefs) + nebular_flux

            return fit_continuum

        @pymc2.deterministic
        def calc_recomb_fluxes(abund_dict=calc_abund_dict, T_He=T_He, ne=ne, cHbeta=cHbeta, xi=1, tau=tau):
            recomb_fluxes = self.calculate_recomb_fluxes(T_He, ne, cHbeta, 1, tau, abund_dict, \
                                                         self.obj_data['recombLine_waves'],
                                                         self.obj_data['recombLine_ions'],
                                                         self.obj_data['recombLine_flambda'])

            return recomb_fluxes

        @pymc2.stochastic(observed=True)  # Likelihood
        def likelihood_ssp(value=self.obj_data['obs_flux_norm_masked'], fit_continuum=calc_continuum,sigmaContinuum=self.obj_data['obs_fluxEr_norm']):
            calc_continuum_masked = fit_continuum * self.obj_data['int_mask']
            chi_F = sum(square(calc_continuum_masked - value) / square(sigmaContinuum))
            return - chi_F / 2

        @pymc2.stochastic(observed=True)  # Likelihood
        def likelihood_recomb(value=self.recomb_fluxes, H_He_TheoFlux=calc_recomb_fluxes, sigmaLines=self.obs_recomb_err):
            chi_F = sum(square(H_He_TheoFlux - value) / square(sigmaLines))
            return - chi_F / 2

        @pymc2.stochastic(observed=True)  # Likelihood
        def likelihood_colExcited(value=self.obs_metal_fluxes, theo_metal_fluzes=calc_colExcit_fluxes, sigmaLines=self.obs_metal_Error):
            chi_F = sum(square(theo_metal_fluzes - value) / square(sigmaLines))
            return - chi_F / 2

        return locals()

    def run_pymc2(self, db_address, iterations = 10000, variables_list = None, prefit = True):

        #Define MCMC model
        self.MAP_Model = pymc2.MAP(self.inf_dict)

        #Prefit:
        if prefit is not False:
            fit_method = prefit if prefit is str else 'fmin_powell'
            print '\n--Starting {} prefit'.format(fit_method)
            start = timer()
            self.MAP_Model.fit(method = fit_method)
            end = timer()
            print 'prefit interval', (end - start)

        #Print prefit data
        print 'Initial conditions:'
        self.display_run_data(self.MAP_Model, variables_list)

        #Launch sample
        print '\nInitiating fit:'
        self.pymc2_M = pymc2.MCMC(self.MAP_Model.variables, db = 'pickle', dbname =  db_address)
        self.pymc2_M.sample(iter=iterations)

        #Save the output csv mean data
        if variables_list != None:
            print '--Saving results in csv'
            self.csv_address = db_address + '_Parameters'
            self.pymc2_M.write_csv(self.csv_address, variables=variables_list)

        #Print again the output prediction for the entire trace
        self.display_run_data(self.MAP_Model, variables_list)

        #Close the database
        self.pymc2_M.db.close()

    def load_pymc_database_manual(self, db_address, burning = 0, params_list = None):

        #Load the pymc output textfile database
        pymc_database = pymc2.database.pickle.load(db_address)

        #Create a dictionaries with the traces and statistics
        traces_dic = {}
        stats_dic = OrderedDict()
        stats_dic['true_values'] = empty(len(params_list))

        #This variable contains all the traces from the MCMC (stochastic and deterministic)
        traces_list = pymc_database.trace_names[0]

        #Get statistics from the run
        for i in range(len(traces_list)):

            trace               = traces_list[i]
            stats_dic[trace]    = OrderedDict()
            trace_array         = pymc_database.trace(trace)[burning:]
            traces_dic[trace]   = trace_array

            if 'dict' not in trace:
                stats_dic[trace]['mean']                    = mean(trace_array)
                stats_dic[trace]['median']                  = median(trace_array)
                stats_dic[trace]['standard deviation']      = std(trace_array)
                stats_dic[trace]['n']                       = trace_array.shape[0]
                stats_dic[trace]['16th_p']                  = percentile(trace_array, 16)
                stats_dic[trace]['84th_p']                  = percentile(trace_array, 84)
                stats_dic[trace]['95% HPD interval']        = (stats_dic[trace]['16th_p'], stats_dic[trace]['84th_p'])
                stats_dic[trace]['trace']                   = trace_array

                if trace in params_list:
                    #Get the right true value key
                    key_true = trace if trace != 'T_He' else 'T_low'

                    #Special cases
                    if key_true == 'ne':
                        key_true = 'n_e'

                    if key_true in self.obj_data: #TODO we need a better structure fo this
                        stats_dic[trace]['true_value'] = self.obj_data[key_true]

                # if params_list is not None:
                #     if trace in params_list:
                #         print trace, stats_dic[trace]['mean']

        #Generate a MCMC object to recover all the data from the run
        dbMCMC = pymc2.MCMC(traces_dic, pymc_database)

        return dbMCMC, stats_dic

    def display_run_data(self, database, variables_list):

        for param in variables_list:
            param_entry = getattr(database, param, None)
            if param_entry is not None:
                try:
                    print '-{} {}'.format(param, param_entry.value)
                except:
                    print 'I could not do it ', param

    # def ready_lines_data(self, ion, lines_labels):
    #
    #     idx_lines = (self.lines_df.index.isin(lines_labels))
    #
    #     self.obj_data[ion + '_labels'] = array(lines_labels)
    #     self.obj_data[ion + '_wave'] = self.lines_df[idx_lines].wavelength.values
    #     self.obj_data[ion + '_pyneb_code'] = self.lines_df[idx_lines].pyneb_code.values
    #
    #     return
    #
    # def load_synthetic_data(self, model):
    #
    #     # Dictionary with data from the object
    #     self.obj_data = dict()
    #
    #     # Physical parameters from the object
    #     self.obj_data['z_star'] = 0.0154
    #     self.obj_data['sigma_star'] = 1.254
    #     self.obj_data['Av_star'] = 0.754
    #
    #     self.obj_data['sigma_gas'] = 2.255
    #
    #     self.obj_data['Hbeta_Flux'] = 1e4
    #
    #     self.obj_data['n_e'] = 120.0
    #     self.obj_data['tau'] = 1.0
    #     self.obj_data['T_low'] = 15500.0
    #     self.obj_data['T_high'] = (1.0807 * self.obj_data['T_low'] / 10000.0 - 0.0846) * 10000.0
    #     self.obj_data['cHbeta'] = 0.1
    #     self.obj_data['xi'] = 1.0
    #     self.obj_data['TSIII'] = 15600.0
    #     self.obj_data['TSIII_error'] = 700
    #     self.obj_data['nSII'] = 130.0
    #     self.obj_data['nSII_error'] = 50.0
    #
    #     self.obj_data['He1_abund'] = 0.085
    #     self.obj_data['He2_abund'] = 0.0
    #
    #     self.obj_data['O2_abund'] = 0.00025
    #     self.obj_data['O3_abund'] = 0.00075
    #
    #     self.obj_data['N2_abund'] = 0.00035
    #
    #     self.obj_data['S2_abund'] = 0.000015
    #     self.obj_data['S3_abund'] = 0.000055
    #
    #     self.obj_data['Ar3_abund'] = 0.00065
    #     self.obj_data['Ar4_abund'] = 0.00012
    #
    #     H1_labels = ['H1_4102A', 'H1_4341A', 'H1_6563A']
    #     self.ready_lines_data('H1', H1_labels)
    #
    #     He1_labels = ['He1_4026A', 'He1_4471A', 'He1_5876A', 'He1_6678A']
    #     self.ready_lines_data('He1', He1_labels)
    #
    #     S2_labels = ['S2_6716A', 'S2_6731A']
    #     self.ready_lines_data('S2', S2_labels)
    #
    #     S3_labels = ['S3_6312A', 'S3_9069A', 'S3_9531A']
    #     self.ready_lines_data('S3', S3_labels)
    #
    #     O2_labels = ['O2_3726A', 'O2_3729A']
    #     self.ready_lines_data('O2', O2_labels)
    #
    #     O3_labels = ['O3_4363A', 'O3_4959A', 'O3_5007A']
    #     self.ready_lines_data('O3', O3_labels)
    #
    #     N2_labels = ['N2_6548A', 'N2_6584A']
    #     self.ready_lines_data('N2', N2_labels)
    #
    #     Ar3_labels = ['Ar3_7136A']
    #     self.ready_lines_data('Ar3', Ar3_labels)
    #
    #     Ar4_labels = ['Ar4_4740A']
    #     self.ready_lines_data('Ar4', Ar4_labels)
    #
    #     # Generate synthetic observation using default values
    #     self.obj_data['mask_stellar'] = OrderedDict()
    #     self.obj_data['mask_stellar']['He1_4026A'] = (4019, 4033)
    #     self.obj_data['mask_stellar']['He1_4471A'] = (4463, 4480)
    #     self.obj_data['mask_stellar']['He1_5876A'] = (5867, 5885)
    #     self.obj_data['mask_stellar']['He1_6678A'] = (6667, 6687)
    #     self.obj_data['mask_stellar']['H1_delta'] = (4090, 4114)
    #     self.obj_data['mask_stellar']['H1_gamma'] = (4329, 4353)
    #     self.obj_data['mask_stellar']['H1_beta'] = (4840, 4880)
    #     self.obj_data['mask_stellar']['H1_alpha'] = (6551, 6575)
    #
    #     return
    # def import_coll_coeff_table(self, hydrogen_lines):
    #
    #     Data_dict = OrderedDict()
    #
    #     for i in range(len(hydrogen_lines)):
    #
    #         Line            = hydrogen_lines[i]
    #         Data_Columns    = [0 + 3*i, 1 + 3*i, 2 + 3*i]
    #         Data_dict[Line] = import_table_data(self.paths_dict['Hydrogen_CollCoeff'], Data_Columns)
    #
    #     return Data_dict



# def calculate_simObservation(self, model, obs_ions, verbose=True):
#
#     # Get physical parameters from model HII region
#     self.sort_emission_types(obs_ions)
#
#     # Prepare the emission spectrum data
#     self.ready_emission_data(obs_ions)
#
#     # Prepare the lines data
#     self.recomb_fluxes = self.calculate_recomb_fluxes(self.obj_data['T_high'], self.obj_data['n_e'],\
#                                                 self.obj_data['cHbeta'], self.obj_data['tau'], \
#                                                 self.obj_data['synth_abund'],
#                                                 self.obj_data['recombLine_waves'],
#                                                 self.obj_data['recombLine_ions'],
#                                                 self.obj_data['recombLine_flambda'])
#
#     self.obs_metal_fluxes = self.calculate_colExcit_flux(self.obj_data['T_low'], self.obj_data['T_high'],
#                                                 self.obj_data['n_e'], self.obj_data['cHbeta'],
#                                                 self.obj_data['synth_abund'],
#                                                 self.obj_data['colLine_waves'],
#                                                 self.obj_data['colLine_ions'],
#                                                 self.obj_data['colLine_flambda'])
#
#     #Errors in the lines are calculated as a percentage
#     self.obs_recomb_err = self.recomb_fluxes * 0.02
#     self.obs_metal_Error = self.obs_metal_fluxes * 0.02
#
#     # -------Prepare stellar continua
#     default_Starlight_file = self.paths_dict['stellar_data_folder'] + 'Dani_Bases_Extra_short.txt'
#     default_Starlight_folder = self.paths_dict['stellar_data_folder'] + 'Bases/'
#     default_Starlight_coeffs = self.paths_dict['stellar_data_folder'] + 'Bases/coeffs_sync_short.txt'
#
#     ssp_lib_dict = self.load_stellar_bases('starlight', default_Starlight_folder, default_Starlight_file, \
#                                            resample_int=1, resample_range=(3600, 6900), norm_interval=(5100, 5150))
#
#     self.stellar_SED = self.calculate_synthStellarSED(self.obj_data['Av_star'], self.obj_data['z_star'],
#                                                       self.obj_data['sigma_star'], \
#                                                       default_Starlight_coeffs, ssp_lib_dict, (4000, 6900),
#                                                       mask_dict=self.obj_data['mask_stellar'])
#
#     # Initial guess number of bases
#     idx_populations = self.stellar_SED['bases_coeff'] > 0.01
#     self.population_limitss = vstack((self.stellar_SED['bases_coeff'][where(idx_populations)] * 0.95,
#                                       self.stellar_SED['bases_coeff'][where(idx_populations)] * 1.05)).T
#     self.nBases = len(where(idx_populations)[0])
#     self.range_bases = arange(self.nBases)
#     columns_to_delete = where(~idx_populations)
#
#     # -------Prepare nebular continua
#     self.idx_Halpha = (self.obj_data['recombLine_labes'] == 'H1_6563A')
#
#     self.Halpha_norm = self.recomb_fluxes[self.idx_Halpha][0] * self.obj_data['Hbeta_Flux'] / self.stellar_SED['normFlux_stellar']
#
#     self.nebular_SED = self.calculate_nebular_SED(self.stellar_SED['stellar_wave_resam'],
#                                                   self.obj_data['z_star'],
#                                                   self.obj_data['cHbeta'],
#                                                   self.obj_data['T_low'],
#                                                   self.obj_data['He1_abund'],
#                                                   self.obj_data['He2_abund'],
#                                                   self.Halpha_norm)
#
#     # Redshift limits for the object
#     z_max_ssp = (self.stellar_SED['stellar_wave_resam'][0] / ssp_lib_dict['basesWave_resam'][0]) - 1.0
#     z_min_ssp = (self.stellar_SED['stellar_wave_resam'][-1] / ssp_lib_dict['basesWave_resam'][-1]) - 1.0
#     self.z_max_ssp_limit = round(z_max_ssp - 0.001, 3)
#     self.z_min_ssp_limit = z_min_ssp
#
#     # -------Emission sed from the object
#     H_He_fluxes = self.recomb_fluxes * self.obj_data['Hbeta_Flux'] / self.stellar_SED['normFlux_stellar']
#     self.emission_Spec = self.calc_emis_spectrum(self.stellar_SED['stellar_wave_resam'],
#                                                  self.obj_data['recombLine_waves'], H_He_fluxes, \
#                                                  self.obj_data['recombLine_waves'], self.obj_data['sigma_gas'],
#                                                  self.obj_data['z_star'])
#
#     # Add the components to be considered in the analysis
#     obs_flux_norm = self.stellar_SED['stellar_flux_norm'] + self.nebular_SED['neb_flux_norm'] + self.emission_Spec
#
#     # Store the data in the object dictionary
#     self.obj_data['normFlux_obs'] = self.stellar_SED['normFlux_stellar']
#     self.obj_data['obs_wave_resam'] = self.stellar_SED['stellar_wave_resam']
#     self.obj_data['obs_flux_norm'] = obs_flux_norm
#     self.obj_data['obs_flux_norm_masked'] = self.obj_data['obs_flux_norm'] * self.stellar_SED['int_mask']
#     self.obj_data['basesWave_resam'] = ssp_lib_dict['basesWave_resam']
#     self.obj_data['bases_flux_norm'] = delete(ssp_lib_dict['bases_flux_norm'], columns_to_delete, axis=0)
#     self.obj_data['int_mask'] = self.stellar_SED['int_mask']
#     self.obj_data['obs_fluxEr_norm'] = self.stellar_SED['stellar_fluxEr_norm']
#
#     # Print the model values
#     if verbose:
#         print '\nInput Parameters:'
#         print '-He1_abund', self.obj_data['He1_abund']
#         print '-n_e', self.obj_data['n_e']
#         print '-T_low', self.obj_data['T_low']
#         print '-T_high', self.obj_data['T_high']
#         print '-cHbeta', self.obj_data['cHbeta']
#         print '-tau', self.obj_data['tau']
#         print '-xi', self.obj_data['xi']
#         print '-TOIII', self.obj_data['TSIII'], '+/-', self.obj_data['TSIII_error']
#         print '-nSII', self.obj_data['nSII'], '+/-', self.obj_data['nSII_error']
#         print '\n-S2_abund', self.obj_data['S2_abund']
#         print '-S3_abund', self.obj_data['S3_abund']
#         print '-O2_abund', self.obj_data['O2_abund']
#         print '-O3_abund', self.obj_data['O3_abund']
#
#         print '-N2_abund', self.obj_data['N2_abund']
#         print '-Ar3_abund', self.obj_data['Ar3_abund']
#         print '-Ar4_abund', self.obj_data['Ar4_abund']
#
#         print '\n-z_star', self.obj_data['z_star']
#         print '-sigma_star', self.obj_data['sigma_star']
#         print '-Av_star', self.obj_data['Av_star']
#
#         print '\n-Wavelength ranges:'
#         print '--Observation:', self.obj_data['obs_wave_resam'][0], self.obj_data['obs_wave_resam'][-1]
#         print '--Bases:', ssp_lib_dict['basesWave_resam'][0], ssp_lib_dict['basesWave_resam'][-1]
#         print '--z min:', self.z_min_ssp_limit
#         print '--z max:', self.z_max_ssp_limit
#         print '--z true:', self.obj_data['z_star']
#
#     return
#
# def sort_emission_types(self, obs_ions):
#
#     # Loop through the ions and read the lines (this is due to the type I format the synth data)
#     lines_labes, lines_waves, lines_ions, lines_abund, lines_pynebCode = [], [], [], [], []
#     abund_dict = {}
#
#     for ion in obs_ions:
#
#         # Recombination lines
#         if ion in ['H1', 'He1', 'He2']:
#             lines_ions += [ion] * len(self.obj_data[ion + '_wave'])
#             lines_labes += list(self.obj_data[ion + '_labels'])
#             lines_waves += list(self.obj_data[ion + '_wave'])
#             lines_pynebCode += list(self.obj_data[ion + '_pyneb_code'])
#
#             if ion == 'H1':
#                 abund_dict[ion] = 1.0
#             else:
#                 abund_dict[ion] = self.obj_data[ion + '_abund']
#
#         # Collisional excited lines
#         else:
#             lines_ions += [ion] * len(self.obj_data[ion + '_wave'])
#             lines_labes += list(self.obj_data[ion + '_labels'])
#             lines_waves += list(self.obj_data[ion + '_wave'])
#             lines_pynebCode += list(self.obj_data[ion + '_pyneb_code'])
#             abund_dict[ion] = self.obj_data[ion + '_abund']
#
#     # Convert lists to numpy arrays
#     lines_labes, lines_waves, lines_ions = array(lines_labes), array(lines_waves), array(lines_ions)
#     lines_pynebCode = array(lines_pynebCode)
#
#     # Sorting by increasing wavelength and by recombination or collisional excited
#     idx_sort = argsort(lines_waves)
#     idx_recomb = in1d(lines_ions[idx_sort], ['H1', 'He1', 'He2'])
#     idx_metals = ~idx_recomb
#
#     # Store the data for later use
#     self.obj_data['recombLine_ions'] = lines_ions[idx_sort][idx_recomb]
#     self.obj_data['recombLine_labes'] = lines_labes[idx_sort][idx_recomb]
#     self.obj_data['recombLine_waves'] = lines_waves[idx_sort][idx_recomb]
#     self.obj_data['recombLine_pynebCode'] = lines_pynebCode[idx_sort][idx_recomb]
#
#     self.obj_data['colLine_ions'] = lines_ions[idx_sort][idx_metals]
#     self.obj_data['colLine_labes'] = lines_labes[idx_sort][idx_metals]
#     self.obj_data['colLine_waves'] = lines_waves[idx_sort][idx_metals]
#     self.obj_data['colLine_pynebCode'] = lines_pynebCode[idx_sort][idx_metals]
#
#     self.obj_data['synth_abund'] = abund_dict
#
#     return
#
#     def ready_emission_data(self, obs_ions, ):
#
#         # Variables to speed up the code
#         self.n_recombLines, self.n_colExcLines = len(self.obj_data['recombLine_labes']), len(self.obj_data['colLine_labes'])
#         self.range_recombLines, self.range_colExcLines =arange(self.n_recombLines), arange(self.n_colExcLines)
#
#         # Readening curves
#         recomblines_xX = self.reddening_Xx(self.obj_data['recombLine_waves'], self.reddedning_curve_model, self.Rv_model)
#         self.obj_data['recombLine_flambda'] = recomblines_xX / self.Hbeta_xX - 1.0
#         colLines_xX = self.reddening_Xx(self.obj_data['colLine_waves'], self.reddedning_curve_model, self.Rv_model)
#         self.obj_data['colLine_flambda'] = colLines_xX / self.Hbeta_xX - 1.0
#
#         # Temperature and density grid parameters #TODO CLEAN add this to conf file
#         min_den, max_den, step_den = 0, 1000, 5
#         min_tem, max_tem, step_tem = 5000, 25000, 10
#
#         # Generate the temperature and density interval
#         self.tem_grid_range = arange(min_tem, max_tem, step_tem)
#         self.den_grid_range = arange(min_den, max_den, step_den)
#         self.den_grid_range[0] = 1 #Change the minimum value for the grid to 1
#
#         # Load Emissivity grids if available or generate them # TODO This code should be able to distinguish if there are missing lines in the grids
#         self.Hbeta_emis_grid = generate_emissivity_grid([4861.0], ['H1'], self.ionDict, self.tem_grid_range, self.den_grid_range)
#
#         if path.isfile(self.paths_dict['recomb_grid']):
#             self.recomb_emis_grid = load_emissivity_grid(self.paths_dict['recomb_grid'])
#         else:
#             self.recomb_emis_grid = generate_emissivity_grid(self.obj_data['recombLine_pynebCode'],
#                                                              self.obj_data['recombLine_ions'], self.ionDict,
#                                                              self.tem_grid_range, self.den_grid_range)
#             save_emissivity_grid(self.paths_dict['recomb_grid'], self.recomb_emis_grid)
#
#
#         if path.isfile(self.paths_dict['collext_grid']):
#             self.metals_emis_grid = load_emissivity_grid(self.paths_dict['collext_grid'])
#         else:
#             self.metals_emis_grid = generate_emissivity_grid(self.obj_data['colLine_pynebCode'],
#                                                              self.obj_data['colLine_ions'], self.ionDict,
#                                                              self.tem_grid_range, self.den_grid_range)
#             save_emissivity_grid(self.paths_dict['collext_grid'], self.metals_emis_grid)
#
#         # Normalize the grids by Hbeta value
#         self.recomb_emis_grid = self.recomb_emis_grid / self.Hbeta_emis_grid
#         self.metals_emis_grid = self.metals_emis_grid / self.Hbeta_emis_grid
#
#         # Establish index of lines which below to high and low ionization zones
#         self.idx_highU = in1d(self.obj_data['colLine_ions'], self.highTemp_ions)
#         self.idx_lowU = ~self.idx_highU
#
#         # Generate an emissivity grid for Hbeta
#         self.Hbeta_emis_grid[:,:,0] = self.ionDict['H1'].getEmissivity(self.tem_grid_range, self.den_grid_range, label = self.Hbeta_pynebCode)
#
#         # Empty Ionic dictionary for the MCMC
#         self.abund_iter_dict = {ion: 0 for ion in obs_ions}
#
#         return