import os
from utils import *
from filters import *
from eeg_functions import *
from eog_functions import *
from ica_functions import *
from erp_functions import *


def eeg_preprocessing_pipeline(S_id, reference_channel, cutoff_low, cutoff_high, filt_order):

    eeg, fs, chanlocs, event_type, event_latency, urevent = load_mat(S_id, 'EEG', os.path.join('data','Raw data','Raw EEG data'))    # loading EEG data

    eeg, chanlocs = rereference_eeg(eeg, chanlocs, reference_channel)  # re-referencing EEG to Cz channel

    eeg, chanlocs, eog, chanlocs_eog, mastoid, chanlocs_mastoid = exclude_non_eeg_channels(eeg, chanlocs)

    # Saving
    save_to_mat(eeg, fs, chanlocs, event_type, event_latency, urevent, S_id, 'EEG_raw_Cz', os.path.join('data','Processed data','Processed EEG data'))
    save_to_mat(eog, fs, chanlocs_eog, event_type, event_latency, urevent, S_id, 'EOG_raw_Cz', os.path.join('data','Processed data','Processed EEG data'))

    plot_multichannel(eeg, fs, chanlocs, event_type, event_latency, S_id, 'EEG_raw_Cz')
    plot_multichannel_fft(eeg, fs, chanlocs, S_id, 'EEG_raw_Cz_fft')

    eeg, event_latency = remove_irrelevant_segments(eeg, fs, event_latency)   # cut pauses before, after and between blocks

    eeg_filt, freq, h = butter_filter(eeg, fs, filt_order, cutoff_low = cutoff_low, cutoff_high = None)     # highpass filtering
    eeg_filt, freq, h = butter_filter(eeg_filt, fs, filt_order, cutoff_low = None, cutoff_high = cutoff_high)    # lowpass filtering

    plot_multichannel(eeg_filt, fs, chanlocs, event_type, event_latency, S_id, filename="EEG_filt")
    plot_multichannel_fft(eeg_filt, fs, chanlocs, S_id, filename="EEG_filt_fft")

    save_to_mat(eeg_filt, fs, chanlocs, event_type, event_latency, urevent, S_id, 'EEG_filt', os.path.join('data','Processed data', 'Processed EEG data'))

    return


def eog_processing_pipeline(S_id, cutoff_low, cutoff_high, numtaps, window, blink_epoch_duration):
    """
    This function processes an EOG (electrooculogram) signal through several steps including
    loading data, removing irrelevant segments, bandpass filtering, and detecting blinks.

    Parameters:
    - S_id: Subject ID used to load the EOG data.
    """

    eog, fs, chanlocs, event_type, event_latency, urevent = load_mat(S_id, 'EOG_raw_Cz', os.path.join('data','Processed data','Processed EEG data'))

    # Remove irrelevant segments from the EOG signal based on event latencies
    eog, event_latency = remove_irrelevant_segments(eog, fs, event_latency)

    # Plot the raw EOG signal and its FFT
    plot_multichannel(eog, fs, chanlocs, None, None, S_id,'EOG')
    plot_multichannel_fft(eog, fs, chanlocs, S_id, 'EOG')

    # Apply band-pass FIR filter to the EOG signal
    eog_filt, freq, f = bandpass_fir_filter(eog, fs, cutoff_low, cutoff_high, numtaps, window)

    # Save
    save_to_mat(eog, fs, chanlocs, event_type, event_latency, urevent, S_id, 'EOG_filt', os.path.join('data','Processed data','Processed EEG data'))

    # Plot the filtered EOG signal and its FFT
    plot_multichannel(eog_filt, fs, chanlocs, None, None, S_id,'EOG_filt')
    plot_multichannel_fft(eog_filt, fs, chanlocs, S_id, 'EOG_filt_fft')

    # Detect blinks in the filtered EOG signal
    blink_epochs, blink_peaks = detect_blinks(eog_filt, fs, blink_epoch_duration)

    plot_multichannel_with_peaks(eog_filt, blink_peaks, fs, chanlocs, S_id, 'EOG_peaks')

    return blink_epochs, blink_peaks


def ica_denoising_pipeline(S_id, blink_epochs, blink_peaks, ortho, extended, blink_epoch_duration, threshold_z):
 
    eeg, fs, chanlocs, event_type, event_latency, urevent = load_mat(S_id, 'EEG_filt', os.path.join('data','Processed data','Processed EEG data'))
    eog, fs, chanlocs_eog, _, _, _ = load_mat(S_id, 'EOG_filt', os.path.join('data','Processed data','Processed EEG data'))

    W_mat, M_mat, components = ICA_get_components(eeg, fs, S_id, ortho, extended)

    eog_artifact_indicies = find_blink_related_components(S_id, components, blink_epochs, blink_peaks, blink_epoch_duration, threshold_z)

    components_to_remove = eog_artifact_indicies
    eeg_denoised = ICA_denoising(W_mat, M_mat, components, components_to_remove)

    plot_multichannel(eeg_denoised, fs, chanlocs, event_type, event_latency, S_id, filename="EEG_denoised")
    plot_multichannel_fft(eeg_denoised, fs, chanlocs, S_id, filename="EEG_denoised_fft")

    save_to_mat(eeg_denoised, fs, chanlocs, event_type, event_latency, urevent, S_id, 'EEG_denoised', os.path.join('data','Processed data', 'Processed EEG data'))

    return


def erp_extraction_pipeline(S_id, epoch_duration, pre_stim_duration, time_window, focused_channel, relevant_channels):  

    eeg, fs, chanlocs, event_type, event_latency, urevent = load_mat(S_id, 'EEG_denoised', os.path.join('data','Processed data', 'Processed EEG data'))

    epochs_1, epochs_2 = segment_into_epoch(eeg, fs, event_type, event_latency, epoch_duration, pre_stim_duration)
    
    epochs_1 = epoch_baseline_correction(epochs_1, fs, pre_stim_duration)
    epochs_2 = epoch_baseline_correction(epochs_2, fs, pre_stim_duration)

    epoch_avg_1 = epoch_averaging(epochs_1)
    epoch_avg_2 = epoch_averaging(epochs_2)

    plot_multichannel(epoch_avg_1, fs, chanlocs, None, None, S_id, 'epoch_avg_1', time_window)
    plot_multichannel(epoch_avg_2, fs, chanlocs, None, None, S_id, 'epoch_avg_2', time_window)
    
    """erp_extraction_per_channel(epoch_avg_1, fs, chanlocs, S_id, 'neutral', time_window, focused_channel)
    erp_extraction_per_channel(epoch_avg_2, fs, chanlocs, S_id, 'incongruent', time_window, focused_channel)

    (n200_amp, n200_latency) = erp_extraxtion_averaged_channels(epoch_avg_1, fs, chanlocs, S_id, 'neutral', time_window, relevant_channels)
    (n200_amp, n200_latency) = erp_extraxtion_averaged_channels(epoch_avg_2, fs, chanlocs, S_id, 'incongruent', time_window, relevant_channels)"""

    single_trial_erp_analysis(epochs_1,fs,chanlocs,S_id,'normal',time_window,'FCZ')

    return

