from django.shortcuts import render
from django.views import View
import os
import requests
import json
from django.views.decorators.csrf import csrf_exempt
from subprocess import call
from django.http import JsonResponse
import random
import string
from rmljson import get_json_path
from settings import BASE_DIR

ckan_base_url = 'http://83.212.100.226/ckan/api/'
mappingpedia_engine_base_url = "http://mappingpedia-engine.linkeddata.es"
#mappingpedia_engine_base_url ="http://83.212.100.226:8090"
#mappingpedia_engine_base_url = "http://localhost:8090"
#mappingpedia_engine_base_url = "http://127.0.0.1:80/"
organization_id = "zaragoza_test"


class Dataset(View):

    def get(self, request):
        if 'organization' in request.GET:
            organizations = [request.GET['organization'].strip()]
            request.session['organization'] = request.GET['organization'].strip()
        elif 'organization' in request.session:
            organizations = [request.sessions['organization']]
        else:
            organizations = get_organizations()
        return render(request, 'dataset_view.html', {'nav': 'dataset', 'organizations': organizations})

    def post(self, request):
        if 'organization' not in request.POST or request.POST['organization'].strip() != '':
            organization = request.POST['organization']
        else:
            organization = organization_id
        url = url_join([mappingpedia_engine_base_url, 'datasets', organization])
        if 'url' in request.POST and request.POST['url'].strip() != '':
            distribution_download_url = request.POST['url']
            data = {
                "distribution_download_url": distribution_download_url,
            }
            if 'name' in request.POST and request.POST['name'].strip() != '':
                data['datasetTitle'] = request.POST['name']
            response = requests.post(url, data)
        elif 'file' in request.FILES:
            distribution_file = request.FILES['file']
            data = {}
            if 'name' in request.POST and request.POST['name'].strip() != '':
                print 'name is sent: %s' % request.POST['name']
                data['datasetTitle'] = request.POST['name']
            response = requests.post(url, files=[('distribution_file', distribution_file)], data=data)
        else:
            print "ERROR"
            return render(request, 'msg.html', {'msg': 'error: no distribution file or URL is passed'})
        if response.status_code == 200:
            dataset_id = json.loads(response.content)['dataset_id']
            return render(request, 'msg.html', {'msg': 'The dataset has been registered with id = '+dataset_id})
        else:
            return render(request, 'msg.html', {'msg': response.content})


class Mapping(View):

    def get(self, request):
        if 'organization' in request.GET:
            organizations = [request.GET['organization'].strip()]
            request.session['organization'] = request.GET['organization'].strip()
        elif 'organization' in request.session:
            organizations = [request.sessions['organization']]
        else:
            organizations = get_organizations()
        datasets = []
        return render(request, 'mapping_view.html', {'datasets': datasets, 'nav': 'mapping',
                                                     'organizations': organizations})

    def post(self, request):
        if 'organization' not in request.POST or request.POST['organization'].strip() != '':
            organization = request.POST['organization']
        else:
            organization = organization_id
        if 'dataset_id' in request.POST:
            dataset_id = request.POST['dataset_id']
        else:
            return render(request, 'msg.html', {'msg': 'dataset id should not be empty'})
        if 'mapping_file_url' in request.POST and request.POST['mapping_file_url'].strip() != '':
            mapping_file_url = request.POST['mapping_file_url']
            url = url_join([mappingpedia_engine_base_url, 'mappings', organization, dataset_id])
            data = {
                "mappingDocumentDownloadURL": mapping_file_url
            }
            response = requests.post(url, data)
        else:
            mapping_file = request.FILES['mapping_file']
            print mapping_file
            url = url_join([mappingpedia_engine_base_url, 'mappings', organization, dataset_id])
            print "the url"
            print url
            response = requests.post(url, files=[('mappingFile', mapping_file)])
        if response.status_code == 200:
            print response.content
            download_url = json.loads(response.content)['mapping_document_download_url']
            #return render(request, 'msg.html', {'msg': 'mappings has been registered with download_url: '+download_url})
            return render(request, 'msg.html',
                          {'msg': 'mappings has been registered with ', 'hreftitle': 'download url',
                           'hreflink': download_url})
        else:
            return render(request, 'msg.html', {'msg': 'error from mappingpedia-engine API: '+response.content})


class Execute(View):

    def get(self, request):
        if 'organization' in request.GET:
            organizations = [request.GET['organization'].strip()]
            request.session['organization'] = request.GET['organization'].strip()
        elif 'organization' in request.session:
            organizations = [request.sessions['organization']]
        else:
            organizations = get_organizations()
        datasets = []#get_datasets()
        return render(request, 'execute_view.html', {'datasets': datasets, 'nav': 'execute',
                                                     'organizations': organizations})

    def post(self, request):
        print "in execution"
        if 'organization' not in request.POST:
            return render(request, 'msg.html', {'msg': 'error: organization is not passed'})
        if 'dataset' not in request.POST:
            return render(request, 'msg.html', {'msg': 'error: dataset is not passed'})
        if 'distribution' not in request.POST:
            return render(request, 'msg.html', {'msg': 'error: distribution is not passed'})
        if 'mapping' not in request.POST:
            return render(request, 'msg.html', {'msg': 'error: mapping is not passed'})
        organization_id = request.POST['organization']
        dataset_id = request.POST['dataset']
        distribution_id = request.POST['distribution']
        mapping_id = request.POST['mapping']
        distribution = get_distribution(distribution_id)
        if distribution is None:
            return render(request, 'msg.html', {'msg': 'error: getting distribution information from CKAN'})
        if distribution['format'].lower().strip() in ['json', 'xml']:
            language = 'rml'
        else:
            language = 'r2rml'
        print "the language is: %s" % language
        url = url_join([mappingpedia_engine_base_url, 'executions2'])
        print url
        data = {
            # "mapping_document_download_url": request.POST['mapping_document_download_url'],
            "mapping_document_id": mapping_id,
            "organization_id":  organization_id,
            "dataset_id": dataset_id,
            "distribution_download_url": distribution['url'],
            "mapping_language": language,
        }
        print "data: "
        print data
        response = requests.post(url, data)
        if response.status_code is 200:
            result_url = json.loads(response.content)['mapping_execution_result_download_url']
            print "result : "
            print response.content
            return render(request, 'msg.html', {'msg': 'Execution results can be found here %s'%result_url})
        else:
            return render(request, 'msg.html', {'msg': 'error from mappingpedia-engine API: '+response.content})


def home(request):
    return render(request, 'home.html')


@csrf_exempt
def webhook(request):
    from settings import BASE_DIR
    try:
        payload = json.loads(request.POST['payload'], strict=False)
        comm = "cd %s; git pull origin master" % BASE_DIR
        print "git pull command: %s" % comm
        call(comm, shell=True)
        return JsonResponse({"status": "Ok"})
    except Exception as e:
        print "git_pull exception: " + str(e)
        return JsonResponse({"error": str(e)})


def get_organizations():
    url = url_join([ckan_base_url, 'action/organization_list'])
    response = requests.get(url)
    organizations = []
    if response.status_code == 200:
        print "status_code is success"
        json_response = json.loads(response.content)
        if "success" in json_response and json_response["success"]:
            print "success ckan"
            organizations = json_response["result"]
        else:
            print "response: " + str(response.content)
    print 'organizations: '
    print organizations
    return organizations


def get_datasets(request):
    print 'get_datasets'
    if 'organization' in request.GET:
        organization = request.GET['organization'].strip()
        print 'organization %s' % organization
        datasets = get_datasets_for_organization(organization, only_contains_distributions=False)
        #print 'datasets: '
        #print datasets
        return JsonResponse({'datasets': datasets})
    else:
        print 'not in organization'
        return JsonResponse({'error': 'organization is not passed'})


def get_datasets_for_organization(organization, only_contains_distributions=False):
    url = url_join([ckan_base_url, 'action', 'organization_show'])
    url += '?id=%s&include_datasets=true' % organization.strip()
    response = requests.get(url)
    print 'get url: '
    print url
    if response.status_code == 200:
        print 'status code is success'
        json_response = json.loads(response.content)
        if "success" in json_response and json_response["success"]:
            print "success ckan"
            datasets_elements = json_response["result"]['packages']
            if only_contains_distributions:
                datasets = [d for d in datasets_elements if len(get_distributions_for_dataset(d['title'], only_original=True))>0]
            else:
                datasets = [d for d in datasets_elements]

            # if only_contains_distributions:
            #     datasets = [d['title'] for d in datasets_elements if len(get_distributions_for_dataset(d['title'], only_original=True))>0]
            # else:
            #     datasets = [d['title'] for d in datasets_elements]
                # ppp = [d for d in datasets_elements[:10]]
                # for p in ppp:
                #     print "printing datasets: "
                #     # print p
                #     print json.dumps(p, indent=4, sort_keys=True)
            return datasets
        else:
            print "response: " + str(response.content)
    else:
        print 'status code is wrong'
    return []


def get_distributions(request):
    if 'dataset' in request.GET:
        distributions = get_distributions_for_dataset(request.GET['dataset'], only_original=True)
        return JsonResponse({'distributions': distributions})
    else:
        return JsonResponse({'error': 'dataset is not passed'})


def get_distributions_for_dataset(dataset_id, only_original=False):
    url = url_join([ckan_base_url, 'action', 'package_show?id='+dataset_id])
    response = requests.get(url)
    if response.status_code == 200:
        print 'get_distributions_for_dataset> status code is success'
        json_response = json.loads(response.content)
        if "success" in json_response and json_response["success"]:
            distributions = json_response['result']['resources']
            if only_original:
                distributions = [d for d in distributions if d['format'].upper() in ['XML', 'JSON', 'CSV']]
            return distributions
        else:
            print "get_distributions_for_dataset> not success"
    else:
        print "get_distributions_for_dataset> not a success status code"
    return []


def get_mappings(request):
    if 'dataset' in request.GET:
        dataset = request.GET['dataset']
        mappings = get_mappings_for_dataset(dataset)
        return JsonResponse({'mappings': mappings})
    return JsonResponse({'error': 'distribution is not passed'})


def get_mappings_for_dataset(dataset):
    url = url_join([mappingpedia_engine_base_url, 'mappings?dataset_id='+dataset.strip()])
    print 'get_mappings_for_dataset> url: '+url
    response = requests.get(url)
    if response.status_code == 200:
        json_response = json.loads(response.content)
        print 'get mappings result:'
        print response.content
        mappings = json_response['results']
    else:
        print 'get mapping status code error'
        mappings = []
    return mappings


def autocomplete(request):
    return render(request, 'autocomplete.html')


def editor_csv(request, download_url, dataset, distribution):
    print "csv editor"
    response = requests.get(download_url)
    if response.status_code == 200:
        line = response.content.split('\n')[0]
        headers = line.split(',')
        return render(request, 'editor.html', {'headers': headers, 'dataset': dataset, 'distribution': distribution})
    else:
        return render(request, 'msg.html', {'error': 'can not download file: ' + download_url})


def editor_json(request, download_url, dataset, distribution):
    print "json editor"
    headers = get_required_headers()
    response = requests.get(download_url, headers=headers)
    print "download url: <%s>" % download_url
    if response.status_code == 200:
        from rmljson import get_json_as_cols
        headers = get_json_as_cols(response.content)
        return render(request, 'editor.html', {'headers': headers, 'dataset': dataset, 'distribution': distribution})
    else:
        return render(request, 'msg.html', {'error': 'can not download file: ' + download_url})


def editor(request):
    if 'dataset' in request.GET and 'distribution' in request.GET:
        dataset = request.GET['dataset'].strip()
        distribution = request.GET['distribution'].strip()
        url = url_join([ckan_base_url, 'action', 'resource_show?id='+distribution])
        print 'resource_show url: '+url
        response = requests.get(url)
        if response.status_code == 200:
            json_response = json.loads(response.content)
            print json_response
            if 'success' in json_response and json_response['success'] is True:
                print json_response
                download_url = json_response['result']['url'].strip()
                if json_response['result']['format'].upper() == 'CSV':
                    return editor_csv(request=request, download_url=download_url, dataset=dataset,
                                      distribution=distribution)
                elif json_response['result']['format'].upper() == 'JSON':
                    return editor_json(request=request, download_url=download_url, dataset=dataset,
                                       distribution=distribution)
                else:
                    return render(request, 'msg.html', {'msg': 'format: '+json_response['result']['format'].upper()})
            else:
                print ' not a success in the ckan reply'
                return render(request, 'msg.html', {'msg': 'ckan API does not return success'})
        else:
            print 'status code is not 200 for getting distribution details'
            return render(request, 'msg.html', {'msg': 'status code is not 200 for getting distritbution details'})
    return render(request, 'msg.html', {'msg': 'dataset and distribution should be passed'})


def get_properties(request):
    if 'concept' in request.GET:
        concept = request.GET['concept'].strip()
        schema_prop_path = os.path.join(BASE_DIR, 'utils','schema-prop.json')
        print 'schema_prop_path: %s' % schema_prop_path
        f = open(schema_prop_path)
        properties_j = json.loads(f.read())
        if concept in properties_j:
            properties = list(set(properties_j[concept]))
            return JsonResponse({'properties': properties})
    return JsonResponse({'properties': []})


def generate_r2rml_mappings(file_name, entity_class, entity_column, mappings):
    from settings import BASE_DIR
    mapping_id = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
    single_property_mapping = """
        rr:predicateObjectMap [
          rr:predicateMap [ rr:constant schema:%s ];
          rr:objectMap    [ rr:termType rr:Literal; rr:column "\\"%s\\""; ];
        ];
    """
    proper_mappings_list = [single_property_mapping % (m["val"].replace('http://schema.org/',''), m["key"].upper()) for m in mappings]
    property_column_mapping = "\n".join(proper_mappings_list)
    mapping_file = """
    @prefix rr: <http://www.w3.org/ns/r2rml#> .
    @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    @prefix dcat: <http://www.w3.org/ns/dcat#> .
    @prefix dct: <http://purl.org/dc/terms/> .
    @prefix mpv: <http://mappingpedia.linkeddata.es/vocab/> .
    @prefix skos: <http://www.w3.org/2004/02/skos/core#> .
    @prefix schema: <http://schema.org/> .
    @base <http://mappingpedia.linkeddata.es/resource/> .
    <%s>
        rr:logicalTable [
            rr:tableName  "\\"%s\\""
        ];

        rr:subjectMap [
            a rr:Subject; rr:termType rr:IRI; rr:class schema:%s;
            rr:column "\\"%s\\"";
        ];
        %s
    .
    """ % (mapping_id, file_name, entity_class, entity_column.upper(), property_column_mapping)
    print mapping_file
    mapping_file_path = os.path.join(BASE_DIR, 'local', mapping_id+'.r2rml.ttl')
    print 'mapping file path:'
    print mapping_file_path
    f = open(mapping_file_path, 'w')
    f.write(mapping_file)
    f.close()
    return mapping_file_path


def generate_rml_mappings(file_name, entity_class, entity_column, mappings, file_url):
    json_path = get_json_path_from_file_url(file_url)
    if json_path is None:
        return None
    from settings import BASE_DIR
    mapping_id = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
    single_property_mapping = """
        rr:predicateObjectMap [
          rr:predicate schema:%s;
          rr:objectMap    [ rml:reference "%s" ]
        ];
    """
    proper_mappings_list = [single_property_mapping % (m["val"].replace('http://schema.org/',''), m["key"]) for m in mappings]
    property_column_mapping = "\n".join(proper_mappings_list)
    mapping_file = """
        @prefix rr: <http://www.w3.org/ns/r2rml#>.
        @prefix rml: <http://semweb.mmlab.be/ns/rml#> .
        @prefix ql: <http://semweb.mmlab.be/ns/ql#> .
        @prefix mail: <http://example.com/mail#>.
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#>.
        @prefix ex: <http://www.example.com/> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>.
        @prefix transit: <http://vocab.org/transit/terms/> .
        @prefix wgs84_pos: <http://www.w3.org/2003/01/geo/wgs84_pos#>.
        @prefix schema: <http://schema.org/>.
        @prefix gn: <http://www.geonames.org/ontology#>.
        @prefix geosp: <http://www.telegraphis.net/ontology/geography/geography#> .
        @base <http://mappingpedia.linkeddata.es/resource/> .
        <%s>
        rml:logicalSource [
            rml:source  "%s";
            rml:referenceFormulation ql:JSONPath;
            rml:iterator "$.%s.*"

        ];

        rr:subjectMap [
            rml:reference "%s";
            rr:class schema:%s
        ];

        %s
    .
    """ % (mapping_id, file_name, ".".join(json_path), entity_column, entity_class, property_column_mapping)
    print mapping_file
    mapping_file_path = os.path.join(BASE_DIR, 'local', mapping_id+'.rml.ttl')
    print 'mapping file path:'
    print mapping_file_path
    f = open(mapping_file_path, 'w')
    f.write(mapping_file)
    f.close()
    return mapping_file_path


def generate_mappings(request):
    print request.POST
    mappings = []
    # if 'file_name' not in request.POST:
    #     return JsonResponse({'error': 'file_name is not passed'})
    if 'entity_class'  not in request.POST:
        return JsonResponse({'error': 'entity_class is not passed'})
    if 'entity_column' not in request.POST:
        return JsonResponse({'error': 'entity_column is not passed'})
    if 'dataset' not in request.POST:
        return JsonResponse({'error': 'dataset is not passed'})
    if 'distribution' not in request.POST:
        return JsonResponse({'error': 'distribution is not passed'})
    distribution = request.POST['distribution'].strip()
    # file_name = request.POST['file_name'].strip()
    entity_class = request.POST['entity_class'].strip()
    entity_column = request.POST['entity_column'].strip()
    dataset = request.POST['dataset'].strip()
    url = url_join([ckan_base_url, 'action', 'package_show?id='+dataset])
    response = requests.get(url)
    if response.status_code == 200:
        json_response = json.loads(response.content)
        organization = json_response["result"]["organization"]["id"]

        for i in range(len(request.POST)):
            key = 'form_key_'+str(i)
            val = 'form_val_'+str(i)
            if key in request.POST and val in request.POST:
                if request.POST[val].strip() != '':
                    element = {"key": request.POST[key], "val": request.POST[val]}
                    mappings.append(element)
            else:
                break
        url = url_join([ckan_base_url, 'action', 'resource_show?id=' + distribution])
        print 'url: '+url
        response = requests.get(url)
        if response.status_code == 200:
            json_response = json.loads(response.content)
            download_url = json_response['result']['url'].strip()

            if json_response['result']['format'].upper() == 'CSV':
                mapping_file = generate_r2rml_mappings(file_name=get_file_from_url(download_url, with_extension=False),
                                                       entity_class=entity_class, entity_column=entity_column,
                                                       mappings=mappings)
            elif json_response['result']['format'].upper() == 'JSON':
                mapping_file = generate_rml_mappings(entity_class=entity_class, entity_column=entity_column,
                                                     file_name=get_file_from_url(download_url, with_extension=True),
                                                     mappings=mappings, file_url=json_response['result']['url'])
            else:
                return render(request, 'msg.html', {'msg': 'the format of distribution file is neither a CSV nor a JSON'})
            if mapping_file is None:
                return render(request, 'msg.html', {'msg': 'mappingpedia is unable to detect a json path of the data'})
            print "mapping_file: "
            print mapping_file
            mapping_file_f = open(mapping_file)
            print mapping_file_f
            url = url_join([mappingpedia_engine_base_url, 'mappings', organization, dataset])
            print "the url to upload mapping"
            print url
            response = requests.post(url, files=[('mappingFile', mapping_file_f)])
            if response.status_code == 200:
                print response.content
                download_url = json.loads(response.content)['mapping_document_download_url']
                # return render(request, 'msg.html', {'msg': 'mappings has been registered with download_url: ' + download_url})
                return render(request, 'msg.html',
                              {'msg': 'mappings has been registered with', 'hreftitle': 'download url',
                               'hreflink': download_url})

            else:
                return render(request, 'msg.html', {'msg': 'error from mappingpedia-engine API: ' + response.content})
    else:
        print 'url: '+url
        return JsonResponse({'error': 'ckan error status code'})


def get_distribution(distribution_id):
    url = url_join([ckan_base_url, 'action/resource_show?id='+distribution_id])
    print 'get distribution url: '+url
    response = requests.get(url)
    if response.status_code == 200:
        json_response = json.loads(response.content)
        return json_response['result']
    else:
        return None


def get_file_from_url(url, with_extension=True):
    """
    :param url:
    :param with_extension: whether the return value contains the extension or not
    :return:
    """
    download_url = url
    if download_url[-1] == '/':
        download_url = download_url[0:-1]
    file_name = download_url.split('/')[-1]
    file_name_no_ext = ".".join(file_name.split('.')[:-1])
    if file_name_no_ext.strip() == '':
        print 'filename has no extension: ' + file_name
        file_name_no_ext = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
    if with_extension:
        return file_name
    else:
        return file_name_no_ext


def get_json_path_from_file_url(url):
    response = requests.get(url, headers = get_required_headers())
    if response.status_code == 200:
        try:
            j = json.loads(response.content)
            return get_json_path(j)['json_path']
        except Exception as e:
            print 'get_json_path_from_file_url> exception: %s' % str(e)
    else:
        print 'get_json_path_from_file_url> error getting the distribution file from url: %s' % url
    return None


def get_required_headers():
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8'
    }
    return headers


def url_join(a):
    sep = "/"
    b = []
    if len(a) == 0:
        return sep
    for aa in a:
        c = aa.strip()
        if c[0] == sep:
            c = c[1:]
        if c[-1] == sep:
            c = c[0:-1]
        b.append(c)
    full_path = sep.join(b)
    return full_path