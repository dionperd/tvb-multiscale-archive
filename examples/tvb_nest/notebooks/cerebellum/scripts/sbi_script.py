# -*- coding: utf-8 -*-

import warnings
import pickle
import torch
from sbi.inference.base import infer, prepare_for_sbi, simulate_for_sbi
from sbi.inference import SNPE
from sbi import utils as utils
from sbi import analysis as analysis

from tvb.contrib.scripts.utils.data_structures_utils import ensure_list

from examples.tvb_nest.notebooks.cerebellum.scripts.base import *
from examples.tvb_nest.notebooks.cerebellum.scripts.tvb_script import run_workflow


def build_priors(config):
    if config.PRIORS_DIST.lower() == "normal":
        priors_normal = torch.distributions.Normal(loc=torch.as_tensor(config.prior_loc),
                                                   scale=torch.as_tensor(config.prior_sc))
        #     priors = torch.distributions.MultivariateNormal(loc=torch.as_tensor(config.prior_loc),
        #                                                     scale_tril=torch.diag(torch.as_tensor(config.prior_sc)))
        priors = torch.distributions.Independent(priors_normal, 1)
    else:
        priors = utils.torchutils.BoxUniform(low=torch.as_tensor(config.prior_min),
                                             high=torch.as_tensor(config.prior_max))
    return priors


def sample_priors_for_sbi(config=None):
    config = assert_config(config, return_plotter=False)
    with open(os.path.join(config.out.FOLDER_RES, 'config.pkl'), 'wb') as file:
        dill.dump(config, file, recurse=1)
    dummy_sim = lambda priors: priors
    priors = build_priors(config)
    simulator, priors = prepare_for_sbi(dummy_sim, priors)
    priors_samples, sim_res = simulate_for_sbi(dummy_sim, proposal=priors,
                                               num_simulations=config.N_SIMULATIONS,
                                               num_workers=config.SBI_NUM_WORKERS)
    return priors_samples, sim_res


def batch_filepath(iB, config, iG=None, filepath=None, extension=None, filename=None):
    if filepath is None or extension is None:
        filepath, extension = os.path.splitext(os.path.join(config.out.FOLDER_RES, filename))
    if iG is None:
        return config.BATCH_FILE_FORMAT % (filepath, iB, extension)
    else:
        return config.BATCH_FILE_FORMAT_G % (filepath, iG, iB, extension)


def batch_priors_filepath(iB, config, iG=None, filepath=None, extension=None):
    return batch_filepath(iB, config, iG, filepath, extension, config.BATCH_PRIORS_SAMPLES_FILE)


def priors_samples_per_batch(priors_samples=None, iG=None, config=None, write_to_files=True):
    config = assert_config(config, return_plotter=False)
    if priors_samples is None:
        priors_samples = sample_priors_for_sbi(config)[0]
    batch_samples = []
    filepath, extension = os.path.splitext(os.path.join(config.out.FOLDER_RES, config.BATCH_PRIORS_SAMPLES_FILE))
    for iB in range(config.N_SIM_BATCHES):
        batch_samples.append(priors_samples[iB::config.N_SIM_BATCHES])
        if write_to_files:
            torch.save(batch_samples[-1], batch_priors_filepath(iB, config, iG, filepath, extension))
    return batch_samples


def priors_samples_per_batch_for_iG(iG, priors_samples=None, config=None, write_to_files=True):
    return priors_samples_per_batch(priors_samples, iG, config, write_to_files)


def generate_priors_samples(config=None):
    from collections import OrderedDict
    from scripts.sbi_script import configure, priors_samples_per_batch_for_iG

    if config is None:
        config = configure()[0]

    print("Gs = %s" % str(config.Gs))
    print("len(Gs)=%d" % len(config.Gs))
    samples = []
    for iG, G in enumerate(config.Gs):
        print('\nG[%d]=%g' % (iG, G))
        samples.append(priors_samples_per_batch_for_iG(iG, config=config, write_to_files=True))
        nBs = len(samples[iG])
        print("len(samples[%d]=%d" % (iG, nBs))
        print("samples[%d][0].shape=%s" % (iG, str(samples[iG][0].shape)))
        print("samples[%d][%d].shape=%s" % (iG, nBs - 1, str(samples[iG][nBs - 1].shape)))
        stats = OrderedDict()
        for p in ["min", "max", "mean", "std"]:
            stats[p] = []
            for iB in range(nBs):
                stats[p].append(getattr(samples[iG][iB], p)(axis=0))
            print("\nsamples[%d][:].%s =\n%s" % (iG, p, str(stats[p])))

        print("\nlen(samples)=%d" % len(samples))

    return samples


def load_priors_samples_per_batch(iB, iG=None, config=None):
    config = assert_config(config, return_plotter=False)
    filepath, extension = os.path.splitext(os.path.join(config.out.FOLDER_RES, config.BATCH_PRIORS_SAMPLES_FILE))
    return torch.load(batch_priors_filepath(iB, config, iG, filepath, extension))


def load_priors_samples_per_batch_per_iG(iB, iG, config=None):
    return load_priors_samples_per_batch(iB, iG, config)


def batch_sim_res_filepath(iB, config, iG=None, filepath=None, extension=None):
    return batch_filepath(iB, config, iG, filepath, extension, config.BATCH_SIM_RES_FILE)


def write_batch_sim_res_to_file(sim_res, iB, iG=None, config=None):
    np.save(batch_sim_res_filepath(iB, assert_config(config, return_plotter=False), iG), sim_res, allow_pickle=True)


def write_batch_sim_res_to_file_per_iG(sim_res, iB, iG, config=None):
    write_batch_sim_res_to_file(sim_res, iB, iG, config)


def simulate_TVB_for_sbi_batch(iB, iG=None, config=None, write_to_file=True):
    config = assert_config(config, return_plotter=False)
    # Get the default values for the parameter except for G
    batch_samples = load_priors_samples_per_batch_per_iG(iB, iG, config)
    n_simulations = batch_samples.shape[0]
    sim_res = []
    for iS in range(n_simulations):
        priors_params = OrderedDict()
        if iG is not None:
            priors_params["G"] = config.Gs[iG]
        for prior_name, prior in zip(config.PRIORS_PARAMS_NAMES, batch_samples[iS]):
            try:
                numpy_prior = prior.numpy()
            except:
                numpy_prior = prior
            if prior_name == "FIC":
                config.FIC = numpy_prior
            elif prior_name == "FIC_SPLIT":
                config.FIC_SPLIT = numpy_prior
            else:
                priors_params[prior_name] = numpy_prior
        if config.VERBOSE:
            print("\n\nSimulation %d/%d for iG=%d, iB=%d" % (iS+1, n_simulations, iG, iB))
            print("Simulating for parameters:\n%s" % str(priors_params))
        sim_res.append(run_workflow(model_params=priors_params, config=config, plot_flag=False, write_files=False)[0])
        if write_to_file:
            write_batch_sim_res_to_file_per_iG(sim_res, iB, iG, config)
    return sim_res


def load_priors_and_simulations_for_sbi(iG=None, priors=None, priors_samples=None, sim_res=None, config=None):
    config = assert_config(config, return_plotter=False)
    if priors is None:
        priors = build_priors(config)
    # Load priors' samples if not given in the input:
    if priors_samples is None:
        # Load priors' samples
        priors_samples = []
        filepath, extension = os.path.splitext(os.path.join(config.out.FOLDER_RES, config.BATCH_PRIORS_SAMPLES_FILE))
        for iB in range(config.N_SIM_BATCHES):
            priors_samples.append(torch.load(batch_priors_filepath(iB, config, iG, filepath, extension)))
        priors_samples = torch.concat(priors_samples)
    # Load priors' samples if not given in the input:
    if sim_res is None:
        # Load priors' samples
        sim_res = []
        filepath, extension = os.path.splitext(os.path.join(config.out.FOLDER_RES, config.BATCH_SIM_RES_FILE))
        for iB in range(config.N_SIM_BATCHES):
            sim_res.append(np.load(batch_sim_res_filepath(iB, config, iG, filepath, extension)))
        sim_res = torch.from_numpy(np.concatenate(sim_res).astype('float32'))
    return priors, priors_samples, sim_res


def filepath_prefixes(filepath, iG=None, iR=None, label=""):
    if iG is not None:
        filepath += "_iG%02d" % iG
    if iR is not None:
        filepath += "_iR%02d" % iR
    if len(label):
        filepath += "_%s" % label
    return filepath


def construct_filepath(default_filepath, config, iG=None, iR=None, label="", filepath=None, extension=None):
    if filepath is None or extension is None:
        filepath, extension = os.path.splitext(os.path.join(config.out.FOLDER_RES, default_filepath))
    filepath = filepath_prefixes(filepath, iG, iR, label)
    return "%s%s" % (filepath, extension)


def posterior_filepath(config, iG=None, iR=None, label="", filepath=None, extension=None):
    return construct_filepath(config.POSTERIOR_PATH, config, iG, iR, label, filepath, extension)


def posterior_samples_filepath(config, iG=None, iR=None, label="", filepath=None, extension=None):
    return construct_filepath(config.POSTERIOR_SAMPLES_PATH, config, iG, iR, label, filepath, extension)


def write_posterior(posterior, iG=None, iR=None, label="", config=None):
    config = assert_config(config, return_plotter=False)
    filepath = posterior_filepath(config, iG, iR, label)
    with open(filepath, "wb") as handle:
        pickle.dump(posterior, handle)


def compute_diagnostics(samples, config, priors=None, map=None, ground_truth=None):
    if priors is None:
        priors = build_priors(config)
    priors_std = priors.stddev.numpy()
    res = {}
    res["samples"] = samples.numpy()
    if map is not None:
        res['map'] = map
    res['mean'] = samples.mean(axis=0).numpy()
    res['std'] = samples.std(axis=0).numpy()
    if ground_truth is not None:
        res["diff"] = ground_truth - res['mean']
        res["accuracy"] = np.maximum(config.MIN_ACCURACY, 100*(1.0 - np.abs(res['diff']/ground_truth)))
        res["zscore"] = res["diff"] / res["std"]
        res["zscore_prior"] = res["diff"] / priors_std
    res["shrinkage"] = 1 - np.power(res['std'], 2) / np.power(priors_std, 2)
    return res


def safely_set_key_list_iR(d, iR, key, defval):
    # Make sure the key exists:
    if key not in d:
        d[key] = []
        if iR == -1:
            iR = 0
    else:
        if not isinstance(d[key], list):
            d[key] = [d[key]]
        if iR == -1:
            iR = len(d[key])
    # Make sure that the size of the d[key] is adequate,
    # by filling in default values:
    while len(d[key]) < iR + 1:
        d[key].append(defval)
    if not isinstance(d[key][iR], list):
        d[key][iR] = [d[key][iR]]
    return d, iR


def safely_append_item_iR(d, iR, key, val):
    # Make sure the key exists and determine iR:
    d, iR = safely_set_key_list_iR(d, iR, key, [])
    # Append now the current value:
    d[key][iR].append(val)
    return d


def write_posterior_samples(results, config,
                            iG=None, iR=None, label="",
                            samples_fit=None, save_samples=True):
    config = assert_config(config, return_plotter=False)
    filepath = posterior_samples_filepath(config, iG, iR, label)
    if samples_fit is None:
        if os.path.isfile(filepath):
            with open(filepath, "rb") as handle:
                samples_fit = pickle.load(handle)
        else:
            samples_fit = {}
    # if iR is None:
    #     iir = -1
    # else:
    #     iir = iR
    # Get G for this run:
    if iG is not None:
        samples_fit["G"] = config.Gs[iG]
    for key, val in results.items():
        samples_fit = safely_append_item_iR(samples_fit, 0, key, val)
    if not save_samples:
        del samples_fit["samples"]
    with open(filepath, "wb") as handle:
        pickle.dump(samples_fit, handle)
    return samples_fit


def load_posterior(iG=None, iR=None, label="", config=None):
    config = assert_config(config, return_plotter=False)
    filepath = posterior_filepath(config, iG, iR, label)
    with open(filepath, "rb") as handle:
        posterior = pickle.load(handle)
    return posterior


def load_posterior_samples(iG=None, iR=None, label="", config=None):
    config = assert_config(config, return_plotter=False)
    filepath = posterior_samples_filepath(config, iG, iR, label)
    with open(filepath, "rb") as handle:
        samples_fit = pickle.load(handle)
    return samples_fit


def add_posterior_samples_iR(all_samples, samples_iR):
    for key, val in samples_iR.items():
        if key != "G":
            if key not in all_samples:
                all_samples[key] = []
            all_samples[key].append(val[0])
    return all_samples


def load_posterior_samples_all_runs(iG, runs=None, label="", samples=None, config=None):
    config = assert_config(config, return_plotter=False)
    if samples is None:
        samples = OrderedDict()
    if runs is None:
        runs = list(range(config.N_FIT_RUNS))
    for iR in runs:
        try:
            samples_iR = load_posterior_samples(iG, iR, label, config)
            samples = add_posterior_samples_iR(samples, samples_iR)
        except Exception as e:
            warnings.warn("Failed to load posterior samples for iG=%d, G=%g, iR=%d!\n%s" % (iG, config.Gs[iG], iR, str(e)))
    return samples


def load_posterior_samples_all_Gs(iGs=None, runs=None, label="", config=None):
    config = assert_config(config, return_plotter=False)
    samples = OrderedDict()
    if iGs is None:
        iGs = range(len(config.Gs))
    for iG in iGs:
        try:
            if runs is False:
                samples[G] = load_posterior_samples(iG, None, label, config)
            else:
                samples[G] = load_posterior_samples_all_runs(iG, runs, label, config=config)
        except Exception as e:
            warnings.warn("Failed to load posterior samples for iG=%d, G=%g!\n%s" % (iG, config.Gs[iG], str(e)))
    return samples


def sbi_train(priors, priors_samples, sim_res, verbose):
    # Initialize the inference algorithm class instance:
    inference = SNPE(prior=priors)
    # Append to the inference the priors samples and simulations results
    # and train the network:
    density_estimator = inference.append_simulations(priors_samples, sim_res).train()
    keep_building = -10
    posterior = None
    exception = "None"
    while keep_building < 0:
        try:
            # Build the posterior:
            if verbose:
                print("Building the posterior...")
            posterior = inference.build_posterior(density_estimator)
            keep_building = 0
        except Exception as e:
            exception = e
            warnings.warn(str(e) + "\nTrying again for the %dth time!" % (10 + keep_building + 2))
            keep_building += 1
    if posterior is None:
        raise Exception(exception)
    return posterior


def sbi_estimate(posterior, target, n_samples_per_run):
    posterior.set_default_x(target)
    return posterior, posterior.sample((n_samples_per_run,)), posterior.map(num_iter=n_samples_per_run)


def sbi_infer(priors, priors_samples, sim_res, n_samples_per_run, target, verbose):
    # Train the neural network to approximate the posterior and return the posterior estimation:
    return sbi_estimate(sbi_train(priors, priors_samples, sim_res, verbose),
                        target, n_samples_per_run)

    
def plot_infer_for_iG(iG, iR=None, samples=None, label="", config=None):
    config = assert_config(config, return_plotter=False)
    if samples is None:
        samples = load_posterior_samples(iG, iR, label, config)
    if iR is None:
        iR = -1
    # Get the default values for the parameter except for G
    params = OrderedDict()
    for pname, pval in zip(config.PRIORS_PARAMS_NAMES, config.model_params.values()):
        params[pname] = pval
    params.update(dict(zip(config.PRIORS_PARAMS_NAMES, samples[config.OPT_RES_MODE][-1])))
    limits = []
    for pmin, pmax in zip(config.prior_min, config.prior_max):
        limits.append([pmin, pmax])
    if config.VERBOSE:
        print("\nPlotting posterior for G[%d]=%g..." % (iG, samples['G']))
    pvals = np.array(list(params.values()))
    labels = []
    for p, pval in zip(config.PRIORS_PARAMS_NAMES, pvals):
        labels.append("%s %s = %g" % (p, config.OPT_RES_MODE, pval)) 
    fig, axes = analysis.pairplot(samples['samples'][iR],
                                  limits=limits,
                                  ticks=limits,
                                  figsize=(10, 10),
                                  labels=labels,
                                  points=pvals,
                                  points_offdiag={'markersize': 6},
                                  points_colors=['r'] * config.n_priors)
    if config.figures.SAVE_FLAG:
        if len(label):
            filename = 'sbi_pairplot_G%g_%s.png' % (samples['G'], label)
        else:
            filename = 'sbi_pairplot_G%g.png' % samples['G']
        plt.savefig(os.path.join(config.figures.FOLDER_FIGURES, filename))
    if config.figures.SHOW_FLAG:
        plt.show()
    else:
        plt.close(fig)
    return fig, axes


def sbi_infer_for_iG(iG, label="", config=None):
    tic = time.time()
    config = assert_config(config, return_plotter=False)
    # Get G for this run:
    G = config.Gs[iG]
    if config.VERBOSE:
        print("\n\nFitting for G = %g!\n" % G)
    # Load the target
    PSD_target = np.load(config.PSD_TARGET_PATH, allow_pickle=True).item()
    if G > 0.0:
        # If we are fitting for a connected network...
        # Duplicate the target for the two M1 regions (right, left) and the two S1 regions (right, left)
        #                                        right                       left
        psd_targ = np.concatenate([PSD_target["PSD_M1_target"], PSD_target["PSD_M1_target"],  # M1
                                   PSD_target["PSD_S1_target"], PSD_target["PSD_S1_target"]]) # S1
    else:
        psd_targ = PSD_target['PSD_target']
    priors, priors_samples, sim_res = load_priors_and_simulations_for_sbi(iG, config=config)
    n_samples = sim_res.shape[0]
    if priors_samples.shape[0] > n_samples:
        warnings.warn("We have only %d simulations for iG=%d, less than priors' samples (=%d)!"
                      % (n_samples, iG, priors_samples.shape[0]))
    samples_fit = None
    if config.N_FIT_RUNS > 0:
        all_inds = list(range(n_samples))
        n_train_samples = int(np.ceil(1.0*n_samples / config.SPLIT_RUN_SAMPLES))
        for iR in range(config.N_FIT_RUNS):
            # For every fitting run...
            if config.VERBOSE:
                print("\n\nFitting run %d!..\n" % iR)
            ticR = time.time()
            # Choose a subsample of the whole set of samples:
            sampl_inds = random.sample(all_inds, n_train_samples)
            # Train the network, build the posterior and sample it:
            posterior, posterior_samples, map = sbi_infer(priors, priors_samples[sampl_inds], sim_res[sampl_inds],
                                                          config.N_SAMPLES_PER_RUN, psd_targ, config.VERBOSE)
            # Write posterior and samples to files:
            write_posterior(posterior, iG, iR, label, config=config)
            diagnostics = compute_diagnostics(posterior_samples, config, priors=priors, map=map, ground_truth=None)
            samples_fit = write_posterior_samples(diagnostics, config, iG, iR, label)
            if config.VERBOSE:
                print("Done with run %d in %g sec!" % (iR, time.time() - ticR))

    # Fit once more using all samples!
    if config.VERBOSE:
        print("\n\nFitting with all samples!..\n")
    ticR = time.time()
    # Train the network, build the posterior and sample it:
    posterior, posterior_samples, map = sbi_infer(priors, priors_samples[:n_samples], sim_res,
                                                  config.N_SAMPLES_PER_RUN, psd_targ, config.VERBOSE)
    # Write posterior and samples to files:
    write_posterior(posterior, iG, iR=None, label=label, config=config)
    diagnostics = compute_diagnostics(posterior_samples, config, priors=priors, map=map, ground_truth=None)
    samples_fit = write_posterior_samples(diagnostics, config, iG, label, samples_fit=samples_fit)
    if config.VERBOSE:
        print("Done with fitting with all samples in %g sec!" % (time.time() - ticR))

    # Plot posterior:
    plot_infer_for_iG(iG, iR=None, samples=samples_fit, config=config);

    if config.VERBOSE:
        print("\n\nFinished after %g sec!" % (time.time() - tic))
        print("\n\nFind results in %s!" % config.out.FOLDER_RES)

    return posterior_samples  # , results, fig, simulator, output_config


def get_train_test_samples(iG, config, n_train_samples=None):
    priors, priors_samples, sim_res = load_priors_and_simulations_for_sbi(iG, config=config)
    n_samples = sim_res.shape[0]
    # Test samples are always going to be the LAST samples:
    n_test_samples = int(np.floor(config.TEST_SAMPLES_RATIO * n_samples))
    test_samples = priors_samples[-n_test_samples:]
    test_res = sim_res[-n_test_samples:]
    if n_train_samples is None:
        n_train_samples = n_samples - n_test_samples
    all_inds = list(range(n_samples))
    sampl_inds = random.sample(all_inds, n_train_samples)
    train_samples = priors_samples[sampl_inds]
    train_res = sim_res[sampl_inds]
    return train_samples, train_res, test_samples, test_res


def sbi_train_for_iG(iG, config, iR=None, n_train_samples=None):
    tic = time.time()
    if config.VERBOSE:
        if iR is None:
            run_str = ""
        else:
            run_str = ", iR=%d" % iR
        print("\nTraining network with %d samples for iG=%d%s!" % (n_train_samples, iG, run_str))
    train_samples, train_res, test_samples, test_res = get_train_test_samples(iG, config, n_train_samples)
    label = "%04d_Train" % train_res.shape[0]
    # Train:
    priors = build_priors(config)
    posterior = sbi_train(priors, train_samples, train_res, config.VERBOSE)
    write_posterior(posterior, iG, iR=iR, label=label, config=config)
    if config.VERBOSE:
        print("\nDone with training with all samples in %g sec!" % (time.time() - tic))
        print("\n\nFind results in %s!" % config.out.FOLDER_RES)
    return posterior, priors, train_samples, train_res, test_samples, test_res


def sbi_test_for_iG(iG, config,
                    iR=None, label="",
                    posterior=None, priors=None, test_samples=None, test_res=None):
    if posterior is None:
        posterior = load_posterior(iG, iR=iR, label=label, config=config)
    if test_samples is None or test_res is None:
        test_samples, test_res = get_train_test_samples(iG, config)[-2:]
    if priors is None:
        priors = build_priors(config)
    if config.VERBOSE:
        if iR is None:
            run_str = ""
        else:
            run_str = ", iR=%d" % iR
        print("\nTesting network for iG=%d%s by sampling %d posterior samples for %d testing samples!" %
              (iG, run_str, config.N_SAMPLES_PER_RUN, test_samples.shape[0]))
    samples_fit = None
    nts = len(test_samples)
    for iT, (ts, rs) in enumerate(zip(test_samples, test_res)):
        if config.VERBOSE:
            print("\nTesting sample... %d/%d" % (iT+1, nts))
        posterior, posterior_samples, map = sbi_estimate(posterior, rs.numpy(), config.N_SAMPLES_PER_RUN)
        # write_posterior(posterior, iG, iR=iR, label=label, config=config)
        diagnostics = compute_diagnostics(posterior_samples, config, priors, map, ts.numpy())
        samples_fit = write_posterior_samples(diagnostics, config, iG, iR, label,
                                              samples_fit=samples_fit, save_samples=False)
    return samples_fit


def sbi_train_and_test_for_iG(iG, config, iR=None, n_train_samples=None):
    tic = time.time()
    # Train:
    posterior, priors, train_samples, train_res, test_samples, test_res = \
        sbi_train_for_iG(iG, config, iR, n_train_samples)
    label = "%04d_Train" % train_res.shape[0]
    # Test:
    samples_fit = sbi_test_for_iG(iG, config, iR, label, posterior, priors, test_samples, test_res)
    if config.VERBOSE:
        print("Done with fitting with all samples in %g sec!"  % (time.time() - tic))
    if config.VERBOSE:
        print("\n\nFinished after %g sec!" % (time.time() - tic))
        print("\n\nFind results in %s!" % config.out.FOLDER_RES)
    return samples_fit


def plot_sbi_fit(config=None):
    FIGWIDTH = 15
    FIGHEIGHT_PER_PRIOR = 5
    RUNS_COLOR = 'k'
    LAST_RUN_COLOR = 'r'
    SAMPLES_MARKER_SIZE = 0.1
    MARKER_MEAN = 'o'
    MARKER_MAP = 'x'
    MARKER_SIZE = 5.0
    SAMPLES_ALPHA = 0.1
    RUNS_ALPHA = 0.5
    PLOT_RUNS = True
    PLOT_SAMPLES = True

    def plot_run(ax, G, map, mean, std, samples=None, is_last=False):
        color = RUNS_COLOR
        alpha = 1.0
        if is_last:
            color = LAST_RUN_COLOR
            alpha = RUNS_ALPHA
        if samples is not None:
            ax.plot([G] * len(samples), samples, marker=MARKER_MEAN,
                    markersize=SAMPLES_MARKER_SIZE, markeredgecolor=color, markerfacecolor=color,
                    linestyle='None', alpha=SAMPLES_ALPHA)
        ax.plot(G, mean, marker=MARKER_MEAN,
                markersize=MARKER_SIZE, markeredgecolor=color, markerfacecolor=color,
                linestyle='None', alpha=alpha)
        ax.plot(G, map, marker=MARKER_MAP,
                markersize=MARKER_SIZE, markeredgecolor=color, markerfacecolor=color,
                linestyle='None', alpha=alpha)
        ax.plot([G] * 2, [mean - std, mean + std], color=color, linestyle='-', linewidth=1, alpha=alpha)
        return ax

    def plot_G(ax, samples, iP):
        n_runs = len(samples['mean'])
        if PLOT_RUNS:
            iR_start = 0
        else:
            iR = n_runs - 1
        for iR in range(iR_start, n_runs):
            ax = plot_run(ax, samples['G'], samples['map'][iR][iP], samples['mean'][iR][iP], samples['std'][iR][iP],
                          samples=samples['samples'][iR][:, iP] if PLOT_SAMPLES else None, is_last=iR == n_runs - 1)
        return ax

    def plot_parameter(ax, iP, pname, samples, is_last=False):
        for G, sg in samples.items():
            ax = plot_G(ax, sg, iP)
        Gs = list(samples.keys())
        if is_last:
            ax.set_xticks(Gs)
            ax.set_xticklabels(Gs)
            ax.set_xlabel("G")
        ax.set_ylabel(pname)
        return ax

    config = assert_config(config, return_plotter=False)
    samples = load_posterior_samples_all_Gs(config)
    fig, axes = plt.subplots(config.n_priors, 1, figsize=(FIGWIDTH, FIGHEIGHT_PER_PRIOR * config.n_priors))
    axes = ensure_list(axes)
    for iP, ax in enumerate(axes):
        axes[iP] = plot_parameter(ax, iP, config.PRIORS_PARAMS_NAMES[iP], samples,
                                  is_last=iP == config.n_priors - 1)
    fig.tight_layout()
    if config.figures.SHOW_FLAG:
        fig.show()
    if config.figures.SAVE_FLAG:
        plt.savefig(config.SBI_FIT_PLOT_PATH)

    return fig, axes


def simulate_after_fitting(iG, iR=None, label="", config=None,
                           workflow_fun=None, model_params={}, FIC=None, FIC_SPLIT=None):

    config = assert_config(config, return_plotter=False)
    with open(os.path.join(config.out.FOLDER_RES, 'config.pkl'), 'wb') as file:
        dill.dump(config, file, recurse=1)

    samples_fit = load_posterior_samples(iG, iR, label, config=config)
    if iR is None:
        iR = -1

    # Get G for this run:
    G = samples_fit['G']  # config.Gs[iG]

    # Get the default values for the parameter except for G
    params = dict(config.model_params)
    params['G'] = G
    # Set the posterior means or maps of the parameters:        
    for pname, pval in zip(config.PRIORS_PARAMS_NAMES, samples_fit[config.OPT_RES_MODE][iR]):
        if pname == "FIC":
            config.FIC = pval
        elif pname == "FIC_SPLIT":
            config.FIC_SPLIT = pval
        else:
            params[pname] = pval
    if FIC is not None:
        config.FIC = FIC
    if FIC_SPLIT is not None:
        config.FIC_SPLIT = FIC_SPLIT
    # Run one simulation with the posterior means:
    if config.VERBOSE:
        print("Simulating using the estimate of the %s of the parameters' posterior distribution!" % config.OPT_RES_MODE)
        print("params =\n", params)
    if workflow_fun is None:
        workflow_fun = run_workflow
    # Specify other parameters or overwrite some:
    params.update(model_params)
    if len(label):
        label = "_%s" % label
    outputs = workflow_fun(plot_flag=True, model_params=params, config=None,
                           output_folder="%s/G%g/STIM%0.2f_Is%0.2f_FIC%0.2f_FIC_SPLIT%0.2f%s" %
                                         (config.output_base, params['G'], params["STIMULUS"],
                                          params['I_s'], config.FIC, config.FIC_SPLIT, label))
    outputs = outputs + (samples_fit, )
    return outputs


def plot_diagnostic_for_iG(iG, diagnostic, config, num_train_samples=None, params=None, runs=None,
                           colors=['b', "g", "m"], marker='.', linestyle='-',
                           ax=None, figsize=None):

    if num_train_samples is None:
        num_train_samples = config.N_TRAIN_SAMPLES_LIST

    if params is None:
        params = config.PRIORS_PARAMS_NAMES

    if figsize is None:
        figsize = config.figures.DEFAULT_SIZE

    if ax is None:
        fig, ax = plt.subplots(nrows=1, ncols=1, figsize=figsize)
    else:
        fig = None

    res = []
    for nts in num_train_samples:
        samples_fit = load_posterior_samples_all_runs(iG, runs, label="%04d_Train" % nts, config=config)
        res.append(np.concatenate(samples_fit[diagnostic]))
    res = np.stack(res)
    res = np.mean(res, axis=1)

    for iP, (param, col) in enumerate(zip(params, colors)):
        ax.plot(num_train_samples, res[:, iP], color=col, marker=marker, markersize=5, linestyle=linestyle,
                label="%s" % param)
        ax.set_title("iG=%d" % iG)
        ax.set_xlabel("N training samples")
        ax.set_ylabel(diagnostic)
        ax.legend()

    if fig is None:
        return ax
    else:
        return ax, fig


def plot_all_together(config, iGs=None, diagnostics=["diff", "accuracy", "zscore_prior", "zscore", "shrinkage"],
                      params=None, num_train_samples=None, runs=None,
                      colors=['b', "g", "m"], marker='.', linestyle='-', figsize=None):

    if iGs is None:
        iGs = list(range(len(config.Gs)))

    if num_train_samples is None:
        num_train_samples = config.N_TRAIN_SAMPLES_LIST

    if params is None:
        params = config.PRIORS_PARAMS_NAMES

    if figsize is None:
        figsize = config.figures.DEFAULT_SIZE

    figsize = np.array(figsize)
    nGs = len(iGs)
    nDs = len(diagnostics)
    figsize[0] = figsize[0] * nDs
    figsize[1] = figsize[1] * nGs
    figsize = tuple(figsize.tolist())

    fig, axes = plt.subplots(nrows=nDs, ncols=nGs, figsize=figsize)
    if nDs == 1:
        axes = axes[np.newaxis]
    elif nGs == 1:
        axes = axes[:, np.newaxis]
    for iD, diagnostic in enumerate(diagnostics):
        for iiG, iG in enumerate(iGs):
            axes[iD, iiG] = plot_diagnostic_for_iG(iG, diagnostic, config, num_train_samples, params, runs,
                                                   colors, marker, linestyle,
                                                   ax=axes[iD, iiG])

    return fig, axes


if __name__ == "__main__":
    parser = args_parser("sbi_script")
    parser.add_argument('--script_id', '-scr',
                        dest='script_id', metavar='script_id',
                        type=int, required=False, default=1, # nargs=1,
                        help="Integer 0 or 1 (default) to select simulate_TVB_for_sbi_batch "
                             "or sbi_infer_for_iG, respectively")
    parser.add_argument('--iB', '-ib',
                        dest='iB', metavar='iB',
                        type=int, required=False, default=0, # nargs=1,
                        help="Batch integer indice. Default=0.")
    parser.add_argument('--iG', '-ig',
                        dest='iG', metavar='iG',
                        type=int, required=False, default=-1, # nargs=1,
                        help="G values' integer indice. Default = -1 will be interpreted as None.")
    parser.add_argument('--iR', '-ir',
                        dest='iR', metavar='iR',
                        type=int, required=False, default=-1,  # nargs=1,
                        help="Run. Default = -1 will be interpreted as None.")
    parser.add_argument('--num_train_samples', '-nts',
                        dest='num_train_samples', metavar='num_train_samples',
                        type=int, required=False, default=-1,  # nargs=1,
                        help="Number of training samples. Default = -1 will be interpreted as None.")

    args, parser_args, parser = parse_args(parser, def_args=DEFAULT_ARGS)
    verbose = args.get('verbose', DEFAULT_ARGS['verbose'])
    if verbose:
        print("Running %s with arguments:\n" % parser.description)
        print(parser_args, "\n")
        print(args, "\n")
    config = configure(**args)[0]
    iR = parser_args.iR
    if iR == -1:
        iR = None
    iG = parser_args.iG
    if parser_args.script_id == 0:
        if iG == -1:
            iG = None
        sim_res = simulate_TVB_for_sbi_batch(parser_args.iB, iG, config=config, write_to_file=True)
    else:
        if iG == -1:
            raise ValueError("iG=-1 is not possible for running sbi_infer_for_iG!")
        elif parser_args.script_id == 1:
            samples_fit_Gs, results, fig, simulator, output_config = sbi_infer_for_iG(iG, config)
        elif parser_args.script_id == 2:
            simulate_after_fitting(iG, iR=iR, config=config,
                                   workflow_fun=None, model_params={}, FIC=None, FIC_SPLIT=None)
        elif parser_args.script_id == 3:
            num_train_samples = parser_args.num_train_samples
            samples_fit = sbi_train_and_test_for_iG(iG, config, iR=iR, n_train_samples=nts)
        elif parser_args.script_id == 4:
            num_train_samples = parser_args.num_train_samples
            samples_fit = sbi_test_for_iG(iG, config, iR, "%04d_Train" % num_train_samples,
                                          posterior=None, priors=None, test_samples=None, test_res=None)
        else:
            raise ValueError("Input argument script_id=%s is neither 0 for simulate_TVB_for_sbi_batch "
                             "nor 1 for sbi_infer_for_iG!")
