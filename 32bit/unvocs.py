#(C) 2022 Takosumi
#This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
#If a copy of the MPL was not distributed with this file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pyworld as pw
import numpy as np
import time

#処理用関数の定義
#所定の範囲を切り出して平均
def average(x, begin, end):
    if begin != end:
        return sum(x[begin:end])/(end - begin)
    else:
        return x[begin]

#線型補間
def incline(c, d, begin, end):
    return np.transpose(np.array([(c * (end - begin - j) + d * j)/(end - begin) for j in range(end - begin)]))

#配列の最初と最後の0を落とす
def cut(a):
    j = 0
    while a[j] == 0:
        j = j + 1
    k = len(a) - 1
    while a[k] == 0:
        k = k - 1
    return a[j:k + 1]

#配列の2乗平均を求める
def rms(a):
    return (sum(np.square(a))/len(a)) ** 0.5

def ave_spec(x, s):
    _, spec_mat, _ = pw.wav2world(x, s)
    spec = sum(spec_mat)/len(x)
    return spec

#母音の音声から変換係数を算出する関数
def estimate_division_pos(a, i, u, e, o, sample_rate):
    norm_a = cut(a)
    k = rms(a)
    norm_i = cut(i) * (k/rms(cut(i)))
    norm_u = cut(u) * (k/rms(cut(u)))
    norm_e = cut(e) * (k/rms(cut(e)))
    norm_o = cut(o) * (k/rms(cut(o)))

    spec_a = ave_spec(norm_a, sample_rate)
    spec_i = ave_spec(norm_i, sample_rate)
    spec_u = ave_spec(norm_u, sample_rate)
    spec_e = ave_spec(norm_e, sample_rate)
    spec_o = ave_spec(norm_o, sample_rate)

    #分割位置推定
    try:
        j = 0
        b = []
        while ((spec_i[j] >= spec_i[j + 1]) or (spec_i[j + 1] < spec_i[j + 2])) and ((spec_u[j] >= spec_u[j + 1]) or (spec_u[j + 1] < spec_u[j + 2])):
            j = j + 1
        k = j
        l = 0
        while not((spec_i[j] > spec_e[j]) and (spec_i[j + 1] < spec_e[j + 1])):
            j = j + 1
        l = l + j
        j = k
        while not((spec_i[j] > spec_o[j]) and (spec_i[j + 1] < spec_o[j + 1])):
            j = j + 1
        l = l + j
        j = k
        while not((spec_u[j] > spec_e[j]) and (spec_u[j + 1] < spec_e[j + 1])):
            j = j + 1
        l = l + j
        j = k
        while not((spec_u[j] > spec_o[j]) and (spec_u[j+1] < spec_o[j + 1])):
            j = j + 1
        b.append(int((l + j)/4))
        j = b[0]
        while (spec_o[j] > spec_a[j]) or (spec_e[j] > spec_a[j]):
            j = j + 1
        if j == b[0]:
            j = j + 1
        b.append(j)
        while spec_a[j] >= spec_a[j + 1]:
            j = j + 1
        while (spec_a[j] < spec_a[j + 1]) or (spec_a[j + 1] >= spec_a[j + 2]):
            j = j + 1
        if j == b[1]:
            j = j + 1
        b.append(j)
        while (spec_e[j] < spec_a[j]):
            j = j + 1
        if j == b[2]:
            j = j + 1
        b.append(j)
        while (spec_i[j - 1] >= spec_i[j]) or (spec_i[j] < spec_i[j + 1]) or spec_i[j] != max(spec_a[j], spec_i[j], spec_u[j], spec_e[j], spec_o[j]):
            j = j + 1
        k = j
        while (spec_e[k] < spec_i[k]):
            k = k - 1
        if k == b[3]:
            k = k + 1
        b.append(k)
        k = j
        while spec_i[j] == max(spec_a[j], spec_i[j], spec_u[j], spec_e[j], spec_o[j]) and ((spec_i[j - 1] <= spec_i[j]) or (spec_i[j] > spec_i[j + 1])):
            j = j + 1
        if j == b[4]:
            j = j + 1
        b.append(j)
        while (max(spec_a[j], spec_i[j], spec_u[j], spec_e[j], spec_o[j]) >= max(spec_a[j + 1], spec_i[j + 1], spec_u[j + 1], spec_e[j + 1], spec_o[j + 1]) or max(spec_a[j + 1], spec_i[j + 1], spec_u[j + 1], spec_e[j + 1], spec_o[j + 1]) < max(spec_a[j + 2], spec_i[j + 2], spec_u[j + 2], spec_e[j + 2], spec_o[j + 2])):
            j = j + 1
        while (((spec_a[j] + spec_i[j] + spec_u[j] + spec_e[j] + spec_o[j]) <= (spec_a[j + 1] + spec_i[j + 1] + spec_u[j + 1] + spec_e[j + 1] + spec_o[j + 1])) or ((spec_a[j + 1] + spec_i[j + 1] + spec_u[j + 1] + spec_e[j + 1] + spec_o[j + 1]) > (spec_a[j + 2] + spec_i[j + 2] + spec_u[j + 2] + spec_e[j + 2] + spec_o[j + 2]))):
            j = j + 1
        if j == b[5]:
            j = j + 1
        b.append(j)
        l = spec_a[j] + spec_i[j] + spec_u[j] + spec_e[j] + spec_o[j] 
        for k in range(j + 1, len(spec_a)):
            if l < spec_a[k] + spec_i[k] + spec_u[k] + spec_e[k] + spec_o[k]:
                l = spec_a[k] + spec_i[k] + spec_u[k] + spec_e[k] + spec_o[k]
                j = k
        while (((spec_a[j] + spec_i[j] + spec_u[j] + spec_e[j] + spec_o[j]) <= (spec_a[j + 1] + spec_i[j + 1] + spec_u[j + 1] + spec_e[j + 1] + spec_o[j + 1])) or ((spec_a[j + 1] + spec_i[j + 1] + spec_u[j + 1] + spec_e[j + 1] + spec_o[j + 1]) > (spec_a[j + 2] + spec_i[j + 2] + spec_u[j + 2] + spec_e[j + 2] + spec_o[j + 2]))):
            j = j + 1
        b.append(j)
    except IndexError:
        for j in range(8 - len(b)):
            b.append(len(spec_a))
    finally:
        k = 8
        for j in range(8):
            if b[j] >= len(spec_a):
                k = j
                break
        if k < 8:
            for j in range(8 - k):
                b[7 - j] = len(spec_a) - j
            for j in range(k):
                if b[k - 1 - j] > b[k - j]:
                    b[k - 1 - j] = b[k - j] - 1

    a = average_calculate(b, spec_a)

    return b, a, spec_a, spec_i, spec_u, spec_e, spec_o

#平均値を計算
def average_calculate(b, s):
    a = []
    a.append(average(s, 0, b[0]))
    a.append(average(s, b[0], b[1]))
    a.append(average(s, b[1], b[2]))
    a.append(average(s, b[2], b[3]))
    a.append(average(s, b[3], b[4]))
    a.append(average(s, b[4], b[5]))
    a.append(average(s, b[5], b[6]))
    a.append(average(s, b[6], b[7]))
    a.append(average(s, b[7], len(s)))
    return a

#声質変換
def voice_convert(s1, a, b1, s2, b2, sample_rate, r):
    incline_length = 5
    h = min([b2[0], b2[1] - b2[0], b2[2] - b2[1], b2[3] - b2[2], b2[4] - b2[3], b2[5] - b2[4], b2[6] - b2[5], b2[7] - b2[6], len(s2) - b2[7]])
    if h < incline_length:
        incline_length = h
    k = int(incline_length/2)
    l = incline_length - k
    b20 = b2[0] - k
    b21 = b2[0] + l
    b22 = b2[1] - k
    b23 = b2[1] + l
    b24 = b2[2] - k
    b25 = b2[2] + l
    b26 = b2[3] - k
    b27 = b2[3] + l
    b28 = b2[4] - k
    b29 = b2[4] + l
    b30 = b2[5] - k
    b31 = b2[5] + l
    b32 = b2[6] - k
    b33 = b2[6] + l
    b34 = b2[7] - k
    b35 = b2[7] + l

    f0, spec_mat, aperiod_mat = pw.wav2world(s1, sample_rate)
    k = len(spec_mat)
    a10 = average(np.transpose(spec_mat), 0, b1[0])
    a11 = average(np.transpose(spec_mat), b1[0], b1[1])
    a12 = average(np.transpose(spec_mat), b1[1], b1[2])
    a13 = average(np.transpose(spec_mat), b1[2], b1[3])
    a14 = average(np.transpose(spec_mat), b1[3], b1[4])
    a15 = average(np.transpose(spec_mat), b1[4], b1[5])
    a16 = average(np.transpose(spec_mat), b1[5], b1[6])
    a17 = average(np.transpose(spec_mat), b1[6], b1[7])
    a18 = average(np.transpose(spec_mat), b1[7], len(spec_mat[0]))
    spec_mat[:, 0:b20] = np.transpose((a10/a[0]) * np.transpose(np.tile(s2[0:b20], (k, 1))))
    spec_mat[:, b20:b21] = incline(a10/a[0], a11/a[1], b20, b21) * s2[b20:b21]
    spec_mat[:, b21:b22] = np.transpose((a11/a[1]) * np.transpose(np.tile(s2[b21:b22], (k, 1))))
    spec_mat[:, b22:b23] = incline(a11/a[1], a12/a[2], b22, b23) * s2[b22:b23]
    spec_mat[:, b23:b24] = np.transpose((a12/a[2]) * np.transpose(np.tile(s2[b23:b24], (k, 1))))
    spec_mat[:, b24:b25] = incline(a12/a[2], a13/a[3], b24, b25) * s2[b24:b25]
    spec_mat[:, b25:b26] = np.transpose((a13/a[3]) * np.transpose(np.tile(s2[b25:b26], (k, 1))))
    spec_mat[:, b26:b27] = incline(a13/a[3], a14/a[4], b26, b27) * s2[b26:b27]
    spec_mat[:, b27:b28] = np.transpose((a14/a[4]) * np.transpose(np.tile(s2[b27:b28], (k, 1))))
    spec_mat[:, b28:b29] = incline(a14/a[4], a15/a[5], b28, b29) * s2[b28:b29]
    spec_mat[:, b29:b30] = np.transpose((a15/a[5]) * np.transpose(np.tile(s2[b29:b30], (k, 1))))
    spec_mat[:, b30:b31] = incline(a15/a[5], a16/a[6], b30, b31) * s2[b30:b31]
    spec_mat[:, b31:b32] = np.transpose((a16/a[6]) * np.transpose(np.tile(s2[b31:b32], (k, 1))))
    spec_mat[:, b32:b33] = incline(a16/a[6], a17/a[7], b32, b33) * s2[b32:b33]
    spec_mat[:, b33:b34] = np.transpose((a17/a[7]) * np.transpose(np.tile(s2[b33:b34], (k, 1))))
    spec_mat[:, b34:b35] = incline(a17/a[7], a18/a[8] * r, b34, b35) * s2[b34:b35]
    spec_mat[:, b35:len(s2)] = np.transpose((a18/a[8]) * r * np.transpose(np.tile(s2[b35:len(s2)], (k, 1))))
    return spec_mat * (rms(a)/rms(s2)), aperiod_mat, f0