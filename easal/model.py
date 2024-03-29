import torch
from torch import nn
from pytorch_transformers import (WEIGHTS_NAME, AdamW, BertConfig,
                                  BertForTokenClassification, BertTokenizer,
                                  WarmupLinearSchedule)


class Ner(BertForTokenClassification):

    def forward(self, input_ids, token_type_ids=None, attention_mask=None, labels=None,valid_ids=None,attention_mask_label=None, args=None, debug=None):
        sequence_output = self.bert(input_ids, token_type_ids, attention_mask, head_mask=None)[0]
        
        if args is not None:
            if args.bert_out == 'cls':
                bert_direct_out = sequence_output[:, 0, :]
            elif args.bert_out == 'lastpool':
                bert_direct_out = self.bert(input_ids, token_type_ids, attention_mask, head_mask=None)[1]
            elif args.bert_out == 'avgpool':
                bert_direct_out = torch.mean(sequence_output, dim=1, keepdim=False)
        else:
            bert_direct_out = sequence_output
        
        batch_size,max_len,feat_dim = sequence_output.shape
        valid_output = torch.zeros(batch_size,max_len,feat_dim,dtype=torch.float32,device='cuda')
        for i in range(batch_size):
            jj = -1
            for j in range(max_len):
                    if valid_ids[i][j].item() == 1:
                        jj += 1
                        valid_output[i][jj] = sequence_output[i][j]
        sequence_output = self.dropout(valid_output)
        logits = self.classifier(sequence_output)

        if labels is not None:
            loss_fct = nn.CrossEntropyLoss(ignore_index=0)
            # Only keep active parts of the loss
            #attention_mask_label = None
            if attention_mask_label is not None:
            
                #if debug == True:
                #    import pdb
                #    pdb.set_trace()
                
                active_loss = attention_mask_label.view(-1) == 1
                active_logits = logits.view(-1, self.num_labels)[active_loss]
                active_labels = labels.view(-1)[active_loss]
                loss = loss_fct(active_logits, active_labels)
            else:
                loss = loss_fct(logits.view(-1, self.num_labels), labels.view(-1))
            return loss
        else:
            return logits, bert_direct_out