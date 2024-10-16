#Read MDF node and property files and generate yaml and tsv data dictionaries
import pandas as pd
import requests
import argparse
import yaml
from ruamel.yaml import YAML as RUAYAML

def readYaml(yamlfile):
    with open(yamlfile) as f:
        configs = yaml.load(f, Loader=yaml.FullLoader)
    return configs

def writeYAML(filename, jsonthing):
    with open(filename, 'w') as f:
        yaml.dump(jsonthing, f)
    f.close()

def runQuery(cdeid, cdever):
    headers = {"accept" : "application/json"}
    url = f"https://cadsrapi.cancer.gov/rad/NCIAPI/1.0/api/DataElement/{cdeid}?version={cdever}"
    try:
        cderes = requests.get(url, headers=headers)
        if cderes.status_code == 200:
            return cderes.json()
        else:
            return "error"
    except requests.exceptions.HTTPError as e:
       print(e)

def getPermValues(cdeid, cdeversion):
    #print(f"CDEID:\t{cdeid}\tVersion:\t{cdeversion}")
    #Sometimes the input Excel identifies URLs as the version
    if 'https' in cdeversion:
        temp = cdeversion.split('=')
        cdeversion = temp[-1]
    cdejson = runQuery(cdeid, cdeversion)
    pvlist = []
    for pventry in cdejson['DataElement']['ValueDomain']['PermissibleValues']:
        pvlist.append(pventry['value'])
    return pvlist

def processProp(node, prop, propjson):
    desc = propjson['PropDefinitions'][prop]['Desc']
    #desc ='Temp'
    enum = None #need a default since enums are defined all over the place
    if 'Req' in propjson['PropDefinitions'][prop]:
        req = propjson['PropDefinitions'][prop]['Req']
    else:
        req = None
    if 'Type' in propjson['PropDefinitions'][prop]:
        datatype = propjson['PropDefinitions'][prop]['Type']
    else:
        datatype = None

    #Does this property have a CDE?
    if 'Term' in propjson['PropDefinitions'][prop]:
        code = propjson['PropDefinitions'][prop]['Term'][0]['Code']
        org = propjson['PropDefinitions'][prop]['Term'][0]['Origin']
        ver = propjson['PropDefinitions'][prop]['Term'][0]['Version']
            #
        # There are two ways enums are listed in MDF.  1) There is an Enum section which has the actual values or  2) Tthe datatype is enum and we need to get the enums from caDSR.
        #
        #Case 1: There is an Enum section:
        if 'Enum' in propjson['PropDefinitions'][prop]:
            enum = propjson['PropDefinitions'][prop]['Enum']
        #Case 2, datatype is enum:
        elif datatype == 'enum':
            enum = getPermValues(code, ver)
        # If neither, then set enum to None.

    else:
        code = None
        org = None
        ver = None
        datatype = None

    return{'Node':node, 'Property':prop, 'Description':desc, 'Required':req, 'Code':code, 'Origin':org, 'Version':ver, 'Type':datatype, 'Enum':enum}
                


def main(args):
    nodejson = readYaml(args.modelfile)
    propjson = readYaml(args.propfile)
    columns = ['Node', 'Property', 'Description', 'Required','Code','Origin','Version' ,'Type', 'Enum']
    final_df = pd.DataFrame(columns=columns)

    handle = nodejson['Handle']
    for node, props in nodejson['Nodes'].items():
        for prop in props['Props']:
            display = True
            if 'Tags' in propjson['PropDefinitions'][prop]:
                if 'Template' in propjson['PropDefinitions'][prop]['Tags']:
                    if propjson['PropDefinitions'][prop]['Tags']['Template'] == 'No':
                        display = False
            if display:
                newline = processProp(node, prop, propjson)
                #print(newline)
                final_df.loc[len(final_df.index)] = newline
                
    #Write a csv file
    csvfile = args.output+".tsv"
    final_df.to_csv(csvfile, sep='\t', index=False)
    #Write a yaml
    yamlfile = args.output+".yml"
    #writeYAML(yamlfile, final_df.to_dict(orient='records'))

    #Alternative writing yaml
    yamlfact = RUAYAML()
    yamlfact.indent(mapping=4, sequence=4, offset=2)
    yamldict = final_df.to_dict(orient='records')
    with open(yamlfile, 'wb') as f:
        yamlfact.dump(yamldict, f)



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--modelfile", required=True, help="MDF Model File")
    parser.add_argument("-p", "--propfile", required=True, help = "MDF Property file")                       
    parser.add_argument("-o", "--output", required=True, help="Output name for csv and yml file")

    args = parser.parse_args()

    main(args)