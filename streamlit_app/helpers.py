import pandas as pd

import plotly.express as px
import plotly.graph_objects as go




# create a function from scratch to calculate integrals of shots
# inputs: file with the raw data, ACR, cut-off.
# returns a data frame with the value of the integrals
# returs plots of grouping and pulses
def calc_shots_integrals(filename, ACR=1, cutoff=40, calibration_factor=1.0):
    # Read the first lines in the file
    lines = []
    with open(filename) as f:
        for i in range(40):
            line = f.readline()
            if not line:
                break
            lines.append(line)
    for n, li in enumerate(lines):
        if li.startswith("Measured at Z:"):
            depth = float(li[15:-1])
            continue
        # elif li.startswith('ACR used:'):
        #     ACR = float(li[10:-1])
        #     continue
        elif li.startswith('Rank used:'):
            rank = int(li[11:-1])
            capacitor = 60 / 1000
            if rank == 1:
                capacitor = 10 / 1000
            elif rank == 2:
                capacitor = 30 / 1000
            elif rank == 4:
                capacitor = 60 / 1000
            elif rank == 8:
                capacitor = 1.8
            continue
        elif li.startswith('Number,Time'):
            lines_to_skip = n
            break
    # now that we have the main values we can start downloading the raw dataframe
    df_orig = pd.read_csv(filename, skiprows=lines_to_skip)
    df = df_orig.copy()
    # only the columns we want
    df = df.loc[:, ['Number', 'Time', 'ch0', 'ch1']]
    # find the zeros
    last_time = df.iloc[-1, 1]
    zeros = df.loc[(df.Time < 1) | (df.Time > last_time - 1), ['ch0', 'ch1']].mean()
    dfzeros = df.loc[:, ['ch0', 'ch1']] - zeros
    dfzeros.columns = ['ch0z', 'ch1z']
    dfz = pd.concat([df, dfzeros], axis=1)
    # calculate doses
    dfz['sensorcharge'] = dfz.ch0z * capacitor
    dfz['cerenkovcharge'] = dfz.ch1z * capacitor
    dfz['dose'] = (dfz.sensorcharge - dfz.cerenkovcharge * ACR) * calibration_factor
    # groupby every 300 ms
    dfz['chunk'] = dfz.Number // (300000 / 700)
    group = dfz.groupby('chunk')
    dfg = group.agg(Time=('Time', 'median'),
                    Time_min=('Time', 'min'),
                    Time_max=('Time', 'max'),
                    ch0z=('ch0z', 'sum'),
                    ch1z=('ch1z', 'sum')
                    )
    dfg['ch0diff'] = dfg.ch0z.diff()

    plotg = px.line(dfg, x='Time', y='ch0z', markers=False)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dfg.Time,
                             y=dfg.ch0z,
                             name='sensor',
                             mode='lines'
                             )
                  )

    fig.add_trace(go.Scatter(x=dfg.Time,
                             y=dfg.ch1z,
                             name='cerenkov',
                             mode='lines'
                             )
                  )
    fig.update_layout(title=dict(text='Signal Grouped every 300 ms'),
                      xaxis=dict(title='time (s)'),
                      yaxis=dict(title='Voltage in capacitor (V)')
                      )

    # Now let's calculate the limits of the integrals
    dfz['shot'] = -1
    starttimes = dfg.loc[dfg.ch0diff > cutoff, 'Time_min']
    finishtimes = dfg.loc[dfg.ch0diff < -cutoff, 'Time_max']
    stss = [starttimes.iloc[0]] + list(starttimes[starttimes.diff() > 2])
    sts = [t - 0.08 for t in stss]
    ftss = [finishtimes.iloc[0]] + list(finishtimes[finishtimes.diff() > 2])
    fts = [t + 0.04 for t in ftss]
    for (n, (s, f)) in enumerate(zip(sts, fts)):
        fig.add_vline(x=s, line_color='green', opacity=0.5, line_dash='dash')
        fig.add_vline(x=f, line_color='red', opacity=0.5, line_dash='dash')
        dfz.loc[(dfz.Time > s) & (dfz.Time < f), 'shot'] = n

    # Find pulses
    maxvaluech = dfz.loc[(dfz.Time < sts[0] - 1) | (dfz.Time > fts[-1] + 1), 'ch0z'].max()
    dfz['pulse'] = dfz.ch0z > maxvaluech * 1.05
    dfz.loc[dfz.pulse, 'pulsenum'] = 1
    dfz.fillna({'pulsenum': 0}, inplace=True)
    dfz['pulsecoincide'] = dfz.loc[dfz.pulse, 'Number'].diff() == 1
    dfz.fillna({'pulsecoincide': False}, inplace=True)
    dfz['singlepulse'] = dfz.pulse & ~dfz.pulsecoincide
    dfz['pulsetoplot'] = dfz.singlepulse * 1

    # now caldulate the integralas over all shots periods
    dfi = dfz.groupby('shot').agg(sensorcharge_nC=('sensorcharge', 'sum'),
                                  cerenkovcharge_nC=('cerenkovcharge', 'sum'),
                                  charge_prop_dose_nC=('dose', 'sum'),
                                  number_pulses=('singlepulse', 'sum')
                                  )
    dfi.reset_index(inplace=True)
    dfig = dfi.loc[dfi.shot != -1, :]

    # Draw pulses plot
    dfz0 = dfz.loc[:, ['Time', 'ch0z']]
    dfz0.columns = ['Time', 'signal']
    dfz0['ch'] = 'ch0z'
    dfz1 = dfz.loc[:, ['Time', 'ch1z']]
    dfz1.columns = ['Time', 'signal']
    dfz1['ch'] = 'ch1z'
    dfztp = pd.concat([dfz0, dfz1])

    fig2 = px.line(dfztp, x='Time', y='signal', color='ch', markers=True)
    fig2.update_traces(marker=dict(size=4))
    fig2.update_xaxes(title='Time (s)')
    fig2.update_yaxes(title='Voltage (V)')
    for (s, f) in zip(sts, fts):
        fig2.add_vline(x=s, line_color='green', opacity=0.5, line_dash='dash')
        fig2.add_vline(x=f, line_color='red', opacity=0.5, line_dash='dash')

    return (fig, dfig, fig2)
