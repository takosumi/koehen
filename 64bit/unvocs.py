#(C) 2022 Takosumi
#This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
#If a copy of the MPL was not distributed with this file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pyworld as pw
import numpy as np

#処理用関数の定義
#所定の範囲を切り出して平均
def average(x, begin, end):
    if begin != end:
        c = x[begin:end]
        d = sum(c)/(end - begin)
    else:
        d = x[begin]
    return d

#線型補間
def incline(c, d, index, begin, end):
    e = (c * (end - index) + d * (index - begin))/(end - begin)
    return e

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
    power = 0
    for i in range(len(a)):
        power = power + (a[i]) ** 2
    return (power/len(a)) ** 0.5

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
            b.append(512)
    finally:
        k = 8
        for j in range(8):
            if b[j] >= 512:
                k = j
                break
        if k < 8:
            for j in range(8 - k):
                b[7 - j] = 512 - j
            for j in range(k):
                if b[k - 1 - j] > b[k - j]:
                    b[k - 1 - j] = b[k - j] - 1

    a = average_calculate(b, spec_a)

    return b, a, spec_a, spec_i, spec_u, spec_e, spec_o

#平均値を計算
def average_calculate(b, spec_a):
    a = []
    a.append(average(spec_a, 0, b[0]))
    a.append(average(spec_a, b[0], b[1]))
    a.append(average(spec_a, b[1], b[2]))
    a.append(average(spec_a, b[2], b[3]))
    a.append(average(spec_a, b[3], b[4]))
    a.append(average(spec_a, b[4], b[5]))
    a.append(average(spec_a, b[5], b[6]))
    a.append(average(spec_a, b[6], b[7]))
    a.append(average(spec_a, b[7], len(spec_a)))
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
    spec_mat2 = []
    for i in range(len(spec_mat)):
        new_spec = [0] * len(spec_mat[0])
        a10 = average(spec_mat[i], 0, b1[0])
        a11 = average(spec_mat[i], b1[0], b1[1])
        a12 = average(spec_mat[i], b1[1], b1[2])
        a13 = average(spec_mat[i], b1[2], b1[3])
        a14 = average(spec_mat[i], b1[3], b1[4])
        a15 = average(spec_mat[i], b1[4], b1[5])
        a16 = average(spec_mat[i], b1[5], b1[6])
        a17 = average(spec_mat[i], b1[6], b1[7])
        a18 = average(spec_mat[i], b1[7], len(spec_mat[i]))
        for j in range (0, b20):
            new_spec[j] = (a10/a[0]) * s2[j]
        for j in range (b20, b21):
            new_spec[j] = incline(a10/a[0], a11/a[1], j, b20, b21) * s2[j]
        for j in range (b21, b22):
            new_spec[j] = (a11/a[1]) * s2[j]
        for j in range (b22, b23):
            new_spec[j] = incline(a11/a[1], a12/a[2], j, b22, b23) * s2[j]
        for j in range (b23, b24):
            new_spec[j] = (a12/a[2]) * s2[j]
        for j in range (b24, b25):
            new_spec[j] = incline(a12/a[2], a13/a[3], j, b24, b25) * s2[j]
        for j in range (b25, b26):
            new_spec[j] = (a13/a[3]) * s2[j]
        for j in range (b26, b27):
            new_spec[j] = incline(a13/a[3], a14/a[4], j, b26, b27) * s2[j]
        for j in range (b27, b28):
            new_spec[j] = (a14/a[4]) * s2[j]
        for j in range (b28, b29):
            new_spec[j] = incline(a14/a[4], a15/a[5], j, b28, b29) * s2[j]
        for j in range(b29, b30):
            new_spec[j] = (a15/a[5]) * s2[j]
        for j in range (b30, b31):
            new_spec[j] = incline(a15/a[5], a16/a[6], j, b30, b31) * s2[j]
        for j in range(b31, b32):
            new_spec[j] = (a16/a[6]) * s2[j]
        for j in range (b32, b33):
            new_spec[j] = incline(a16/a[6], a17/a[7], j, b32, b33) * s2[j]
        for j in range(b33, b34):
            new_spec[j] = (a17/a[7]) * s2[j]
        for j in range (b34, b35):
            new_spec[j] = incline(a17/a[7], (a18/a[8]) * r, j, b34, b35) * s2[j]
        for j in range(b35, len(s2)):
            new_spec[j] = (a18/a[8] * r) * s2[j]
        spec_mat2.append(new_spec)
    spec_mat = np.array(spec_mat2) * (rms(a)/rms(s2))

    return spec_mat, aperiod_mat, f0