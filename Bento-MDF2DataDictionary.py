# https://cbiit.github.io/bento-mdf/example.html
from bento_mdf.mdf import MDF
import argparse
import pandas as pd
from ruamel.yaml import YAML as RUAYAML
from crdclib import crdclib as crdc


def getPermValues(cdeid, cdeversion):
    cdejson = crdc.getCDERecord(cdeid, cdeversion)
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

    configs = crdc.readYAML(args.config)

    #temp_files = []
    #for file in configs['Input']['mdffiles']:
    #    temp_files.append(configs['Input']['in_dir']+file)
    #According to Nelson, MDF will late a list of files if the unpacking operator is used (*)
    temp_files = configs['Input']['mdffiles']
    mdf_working = MDF(*temp_files, handle = configs['Input']['handle'])

    # First step is to create a dataframe of all properties that have allowable values, etiher as an enum section or as a CDE reference with PVs
    columns = ['Node', 'Property', 'Description', 'Required','Code','Origin','Version' ,'DataType', 'Enum']
    final_df = pd.DataFrame(columns=columns)

    # Turns out for a data dictionary, we only need to create a props entity
    nodes = mdf_working.model.nodes
    props = mdf_working.model.props
    modelversion = mdf_working.version
    modelname = mdf_working.handle
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
        code = None
        version = None
        origin = None
        enum = None
        termhandle = None
        #Get the information from the props section
        node = prop[0]
        propname = prop[1]
        desc = props[prop].get_attr_dict()['desc']
        req = props[prop].get_attr_dict()['is_required']
        datatype = props[prop].get_attr_dict()['value_domain']

        # And now to start digging into terms using the concept.terms approach.  That seems the easiest way to manage the prop-term relationshisps.
        if mdf_working.model.props[prop].concept is not None:
            workingterms = mdf_working.model.props[prop].concept.terms.values()
            for workingtermobj in workingterms:
                workingterm = workingtermobj.get_attr_dict()
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
                enum = getPermValues(code, version)

        temp = {'Node' : node, 'Property': propname, 'Description':desc, 'Required':req,'Code':code,'Origin':origin,'Version':version ,'DataType':datatype, 'Enum':enum}
        final_df.loc[len(final_df.index)] = temp


    outfile = configs['Output']['out_dir']+configs['Output']['filename']

    #Write a csv file
    csvfile = outfile+".tsv"
    final_df.to_csv(csvfile, sep='\t', index=False)

    #Write a yaml file
    yamlfile = outfile+".yml"
    writeFormattedYaml(yamlfile, final_df)

    #Write node specific files
    nodelist = final_df.Node.unique()
    for node in nodelist:
        node_df = final_df.loc[final_df['Node'] == node]
        csvfilename = outfile+"_"+node+".tsv"
        yamlfilename = outfile+"_"+node+".yml"
        writeFormattedYaml(yamlfilename, node_df)
        node_df.to_csv(csvfilename, sep='\t', index=False)
        
    #Create submission sheets if requestsed
    if args.submissionfiles:
        loadsheets = {}
        for node in nodelist:
            props = nodes[node].props
            loadsheets[node] = pd.DataFrame(columns=list(props.keys()))
        for node, df in loadsheets.items():
            #add the type column
            df.insert(0, 'type', node)
            #TODO: Add linking columns
            filename = configs['Output']['out_dir']+modelname+"Data_Loading_Template_"+node+"_v"+modelversion+".csv"
            df.to_csv(filename, sep="\t", index=False)
        
         

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", required=True, help="location and name of configuration file")
    parser.add_argument("-s", "--submissionfiles", action='store_true', help="Create empty submission files")

    args = parser.parse_args()

    main(args)