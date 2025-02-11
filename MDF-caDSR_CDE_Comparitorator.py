# The purpose of this script is to look at the names and descriptions of a property in MDF and see if they match the name and description in cDSR
from crdclib import crdclib
import argparse
import bento_mdf
import pandas as pd



def getIdentifiers(propkey, mdf):
    cdeid = None
    cdever = None
    terms = mdf.model.props[propkey].concept.terms
    for term in terms.values():
        if term.get_attr_dict()['origin_name'] == 'caDSR':
            cdeid = term.get_attr_dict()['origin_id']
            cdever = term.get_attr_dict()['origin_version']
    return cdeid, cdever


def parseCDEJSON(cdejson, modelname):
    if cdejson['status'] == 'success':
        cde_definition = cdejson['DataElement']['definition']
        cde_longname = cdejson['DataElement']['longName']
        # It looks like there can be multiple entries for Alternate Names
        # For CDE 7572817, CRDC has two
        altlist = []
        for entry in cdejson['DataElement']['AlternateNames']:
            if entry['context'] == modelname:
                altlist.append({modelname: entry['name']})
            elif entry['context'] == 'CRDC':
                altlist.append({'CRDC': entry['name']})
    return {'def': cde_definition, 'ln': cde_longname, 'alt': altlist}

def addString(stringthing, addthis):
    if stringthing is None:
        stringthing = addthis
    else:
        stringthing = stringthing+"|"+addthis
    return stringthing

def matchAnalysis(df):
    temp_df = pd.DataFrame(columns=['comment'])
    for index, row in df.iterrows():
        restring = None
        if row['modelDef'] == row['cdeDef']:
            restring = addString(restring, "Definition Match")
        else:
            restring = addString(restring, "Definition Mismatch")
        if row['modelPropName'] == row['cdePropName']:
            restring = addString(restring, "Name Match")
        else:
            restring = addString(restring, "Name Mismatch")
        if row['modelPropName'] == row['altPropName']:
            restring = addString(restring, "Alt Name Match")
        else:
            restring = addString(restring, "Alt Name Mismatch")
        temp_df.loc[len(temp_df)] = {'comment': restring}
        new_df = pd.concat([df, temp_df], axis=1)
    return new_df

def main(args):
    configs = crdclib.readYAML(args.configfile)
    
    mdf =  bento_mdf.MDF(*configs['Input']['mdffiles'])
    
    props = mdf.model.props
    
    columns = ['model', 'cdeid', 'cdeVersion', 'modelDef', 'cdeDef', 'modelPropName', 'cdePropName', 'altPropName']
    res_df = pd.DataFrame(columns=columns)
    
    for propkey, propobj in props.items():
        if mdf.model.props[propkey].concept is not None:
            model_desc = propobj.get_attr_dict()['desc']
            model = propobj.get_attr_dict()['model']
            model_propname = propobj.get_attr_dict()['handle']
            cdeid, cdeversion = getIdentifiers(propkey, mdf)
            cdejson = crdclib.getCDERecord(cdeid, cdeversion)
            cdeinfo = parseCDEJSON(cdejson, model)
            for entry in cdeinfo['alt']:
                for altname in entry.values():
                    res_df.loc[len(res_df)] = {'model': model, 'cdeid': cdeid, 'cdeVersion': cdeversion, 'modelDef': model_desc, 'cdeDef': cdeinfo['def'], 
                                           'modelPropName': model_propname, 'cdePropName': cdeinfo['ln'], 'altPropName': altname}
    res_df = matchAnalysis(res_df)
    
    outputfile = configs['Output']['out_dir']+configs['Output']['filename']
    res_df.to_csv(outputfile, sep="\t", index=False)
            
    
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--configfile", required=True,  help="Configuration file containing all the input info")
    parser.add_argument("-v", "--verbose", help="Verbose Output")

    args = parser.parse_args()

    main(args)