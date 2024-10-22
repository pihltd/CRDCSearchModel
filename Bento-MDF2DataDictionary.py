# https://cbiit.github.io/bento-mdf/example.html
from bento_mdf.mdf import MDF
import argparse
import pandas as pd
import requests
from ruamel.yaml import YAML as RUAYAML

def runcaDSRQuery(cdeid, cdever):
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
    #Sometimes the input Excel identifies URLs as the version
    #if 'https' in cdeversion:
    #    temp = cdeversion.split('=')
    #    cdeversion = temp[-1]
    cdejson = runcaDSRQuery(cdeid, cdeversion)
    pvlist = []
    for pventry in cdejson['DataElement']['ValueDomain']['PermissibleValues']:
        pvlist.append(pventry['value'])
    return pvlist

def writeFormattedYaml(filename, df):
    yamlfact = RUAYAML()
    yamlfact.indent(mapping=4, sequence=4, offset=2)
    yamldict = df.to_dict(orient='records')
    with open(filename, 'wb') as f:
        yamlfact.dump(yamldict, f)   

def main(args):
    mdf_working = MDF(args.modelfile, args.propfile, handle=args.handle)

    # First step is to create a dataframe of all properties that have allowable values, etiher as an enum section or as a CDE reference with PVs
    columns = ['Node', 'Property', 'Description', 'Required','Code','Origin','Version' ,'DataType', 'Enum']
    final_df = pd.DataFrame(columns=columns)

    #nodes = mdf_working.model.nodes
    props = mdf_working.model.props
    #terms = mdf_working.model.terms


    #Where to find:
    # Node - nodes, props
    # Property - props
    # Description - props
    # Required - props
    # Code - terms
    # Origin - terms
    # Version - terms
    # type - props
    # enum - terms

    for prop in props:
        #print(prop)
        code = None
        version = None
        origin = None
        enum = None
        termhandle = None
        node = prop[0]
        propname = prop[1]
        #print(props[prop].get_attr_dict())
        desc = props[prop].get_attr_dict()['desc']
        req = props[prop].get_attr_dict()['is_required']
        datatype = props[prop].get_attr_dict()['value_domain']
        prophandle = props[prop].get_attr_dict()['handle']
        if mdf_working.model.props[prop].concept is not None:
            workingterms = mdf_working.model.props[prop].concept.terms.values()
            #print(workingterms)
            for workingtermobj in workingterms:
                workingterm = workingtermobj.get_attr_dict()
                #print(workingterm)
                code = workingterm['origin_id']
                if 'origin_version' in workingterm:
                    version = workingterm['origin_version']
                    #Need to clean up some labelling mistakes
                    if 'https' in version:
                        temp = version.split('=')
                        version = temp[-1]
                else:
                    version = '1'
                origin = workingterm['origin_name']
                termhandle = workingterm['handle']
                enum = getPermValues(code, version)

        temp = {'Node' : node, 'Property': propname, 'Description':desc, 'Required':req,'Code':code,'Origin':origin,'Version':version ,'DataType':datatype, 'Enum':enum}
        final_df.loc[len(final_df.index)] = temp
        #if termhandle is not None:
        #    print(f"Prop Handle:\t{prophandle}\tTerm Handle:\t{termhandle}")
        #print(temp)

    outdir = '/home/pihl/mockdata/'    

    #Write a csv file
    csvfile = outdir+args.output+".tsv"
    final_df.to_csv(csvfile, sep='\t', index=False)

    #Write a yaml file
    yamlfile = outdir+args.output+".yml"
    writeFormattedYaml(yamlfile, final_df)

    #Write node specific files
    nodelist = final_df.Node.unique()
    for node in nodelist:
        node_df = final_df.loc[final_df['Node'] == node]
        csvfilename = outdir+node+"_"+args.output+".tsv"
        yamlfilename = outdir+node+"_"+args.output+".yml"
        writeFormattedYaml(yamlfilename, node_df)
        node_df.to_csv(csvfilename, sep='\t', index=False)
     

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--modelfile", required=True, help="MDF Model File")
    parser.add_argument("-p", "--propfile", required=True, help = "MDF Property file") 
    parser.add_argument("-d", "--handle", required=True, help= "MDF Model Handle name")                  
    parser.add_argument("-o", "--output", required=True, help="Output name for csv and yml file")

    args = parser.parse_args()

    main(args)