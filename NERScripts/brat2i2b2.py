# Copyright (c) 2016-2017 Fred Hutchinson Cancer Research Center
#
# Licensed under the Apache License, Version 2.0: http://www.apache.org/licenses/LICENSE-2.0
#
'''
This script takes a BRAT directory containing .ann and .txt files (among possible other format types as well)
and converts the .ann and .txt files into the i2b2 training directory format in the defined
output directory.

EG:
{DIR}/brat_data/train/           <------The input dir
                  |-file1.ann
                  |-file2.ann
                  |-config.conf
                  |-file1.txt
                  |-file2.txt


{DIR}/i2b2_data/train/           <------The output dir
                  |-concept
                  |    |-file1.con
                  |    |-file2.con
                  |    |-etc
                  |-txt
                  |    |-file1.txt
                  |    |-file2.txt

'''
import os
import re
import spacy

# directory where brat .txt and .ann files live
in_dir = "/home/wlane/bratserv/PHI_testing_data_e"
out_dir = "/home/wlane/nethome/i2b2_data/deidentification_test"
nlp = spacy.load('en')

# read documents into memory
ann_dict = dict()
txt_dict = dict()

doc_paths = list()
for file in os.listdir(in_dir):
    if file.endswith(".txt"):
        doc_paths.append(os.path.join(in_dir, file))

for dpath in doc_paths:
    ann_file = os.path.join(in_dir, dpath.split("/")[-1].split(".")[0] + ".ann")

    if not os.stat(ann_file).st_size == 0: # if there are annotations for this document, we want to keep them
        with open(dpath, "rb") as f:
            text = f.read()
            txt_dict[dpath.split(os.sep)[-1].split(".")[0]] = text
        with open(ann_file, "rb") as a:
            ann = a.read()
            ann_dict[ann_file.split(os.sep)[-1].split(".")[0]] = ann

# break into sentences
for did, txt in txt_dict.items():
    processed_txt = nlp(txt.decode("utf-8"))
    proc_sentences = [sent for sent in processed_txt.sents]

    # split annotation for this doc into tuple, sort by lowest start span
    curr_doc_annotation = ann_dict[did]
    curr_doc_annotation_split = curr_doc_annotation.split("\n")
    ordered_annotations = list()
    for i, single_ann in enumerate(curr_doc_annotation_split):
        ann_pieces = single_ann.split("\t")
        if len(ann_pieces)>1:
            label = ann_pieces[1].split()[0]
            start = int(ann_pieces[1].split()[1])
            stop = int(ann_pieces[1].split()[-1])
            text = ann_pieces[2]
            ordered_annotations.append((start, stop, label, text))
    ordered_annotations = sorted(ordered_annotations, key=lambda x: x[0])


    # for each token in each sentence, match the label: tuple(token, label) for token in sentence
    ann_idx = 0
    document_tokens= list()
    for sent_num, sent in enumerate(proc_sentences):
        sent_tokens = list()
        tok_count = -1
        for tok in sent:
            if not re.match(r'^\s*$', tok.orth_): # if the token is just whitespace, dont count or include it
                tok_count+=1
                if ann_idx < len(ordered_annotations):
                    if tok.idx >= ordered_annotations[ann_idx][0] and tok.idx < ordered_annotations[ann_idx][1]:
                        #  tuple( text, sent_num, tok_num, tag, full_text)
                        tok_text = tok.orth_.strip()
                        tok_n_label = (tok_text, sent_num, tok_count, ordered_annotations[ann_idx][2], ordered_annotations[ann_idx][3])
                        sent_tokens.append(tok_n_label)
                    if tok.idx > ordered_annotations[ann_idx][1]:
                        ann_idx += 1

        document_tokens.append(sent_tokens)

    # consolidate list of sentence tokens into i2b2 format labels, write to file
    i2b2_entries_for_doc = list()

    if not os.path.exists(os.path.join(out_dir,"con")):
        os.makedirs(os.path.join(out_dir,"con"))
    with open(os.path.join(out_dir,"con", did + ".con"), "wb") as out_f:
        for s in document_tokens:
            same_labels = dict()
            if len(s) > 0:
                for tok in s:
                    if tok[4] not in same_labels:
                        same_labels[tok[4]] = list()
                    same_labels[tok[4]].append(tok)
            # form annotation string for this sentence
            text = ""
            sent_num=0
            label = ""
            for k, v in same_labels.items():
                string = "c="
                max_tok_num = float("-inf")
                min_tok_num = float("inf")
                for t in v:
                    if t[2] > max_tok_num:
                        max_tok_num = t[2]
                    if t[2] < min_tok_num:
                        min_tok_num = t[2]
                    text=k
                    sent_num = t[1]
                    label = t[3]
                string += "\""+text+"\" " +str(sent_num+1)+":"+str(min_tok_num) + ' ' + str(sent_num+1) + ":" + str(max_tok_num) + "||t=\"" + label + "\""
                print string
                out_f.write(string + "\n")


    # print lines as txt files
    if not os.path.exists(os.path.join(out_dir,"txt")):
        os.makedirs(os.path.join(out_dir,"txt"))
    with open(os.path.join(out_dir, "txt", did + ".txt"), "wb") as txt_out:
        for sent in proc_sentences:
            for i, tok in enumerate(sent):
                if "\n" not in tok.orth_:
                    txt_out.write(tok.orth_.encode("utf-8"))
                    if i < len(sent):
                        txt_out.write(" ")
            txt_out.write("\n")
print "Finished converting Brat txt and ann files to i2b2 txt and con format."