from pathlib import Path
import pandas as pd
import json
from jinja2 import Template
import logging
import os, sys, subprocess
import yaml
import signal

log_format = '%(levelname)-8s %(asctime)s   %(message)s'
date_format = "%d/%m %H:%M:%S"
logging.basicConfig(format=log_format, datefmt=date_format, level=logging.DEBUG)

class Dict2Class(object):
      
    def __init__(self, my_dict):
          
        for key in my_dict:
            setattr(self, key, my_dict[key])
    
    def print_references(self):
        text = ""
        for r in self.references:
            text = "\n".join([text, f"- {r}"])
        return text

def load_project_metadata(path_to_metadata):
    with open(path_to_metadata, "r") as f:
        project_metadata = json.load(f)
        p = list(project_metadata.values())[0]
        p['name'] = [i for i in project_metadata.keys()][0]
        p = Dict2Class(p)
    return p

def generate_mkdocs_report(bgcflow_dir, project_name, port=9999, fileserver_port=9998, ipynb=True):
    logging.info("Checking input folder..")

    # is it a bgcflow data directory or just a result directory?
    input_dir = Path(bgcflow_dir)
    if (input_dir / 'metadata/project_metadata.json').is_file():
        report_dir = input_dir
    else:
        report_dir = input_dir / f"data/processed/{project_name}"
        assert (report_dir / 'metadata/project_metadata.json').is_file(), "Unable to find BGCFlow results"
    logging.debug(f"Found project_metadata. Using [{report_dir}] as report directory.")

    # Get project metadata
    p = load_project_metadata(report_dir / 'metadata/project_metadata.json')
    assert p.name == project_name, "Project metadata does not match with user provided input!"
    logging.debug(f"Project [{p.name}] was analysed using BGCFlow version {p.bgcflow_version}")

    # available reports, check all output files
    logging.debug(f"Available reports: {list(p.rule_used.keys())}")
    df_results = pd.DataFrame.from_dict(p.rule_used).T

    # check available reports
    logging.info(f"Generating mkdocs config at: {report_dir / 'mkdocs.yml'}")
    if ipynb:
        extension = "ipynb"
    else:
        extension = "md"
    for r in p.rule_used.keys():
        jupyter_template = report_dir / f"docs/{r}.{extension}"
        #logging.debug(jupyter_template.is_file()) # TO DO ASSERT IPYNB FILES, THEY SHOULD BE IN THE DOCS
        logging.debug(f"Adding report [{r} : {jupyter_template.name}]")
        mkdocs_template['nav'].append({r : jupyter_template.name})
    with open(report_dir / 'mkdocs.yml', "w") as f:
        yaml.dump(mkdocs_template, f)

    # Generate index.md
    docs_dir = report_dir / 'docs'
    docs_dir.mkdir(exist_ok=True, parents=True)
    logging.info(f"Generating homepage at: {docs_dir / 'index.md'}")
    df_results.loc[:, "BGCFlow_rules"] = df_results.index
    df_results = df_results.loc[:, ["BGCFlow_rules", "description"]].reset_index(drop=True)
    df_results.loc[:, "BGCFlow_rules"] = [f"[{i}]({i}/)"+"{.md-button}" for i in df_results.loc[:, "BGCFlow_rules"]]
    data = {'p_name' : p.name,
            'p_description' : p.description,
            'p_sample_size' : p.sample_size,
            'p_references' : p.references,
            'rule_table' : df_results.to_markdown(index=False)
           }
    j2_template = Template(index_template)
    with open(docs_dir / "index.md", "w") as f:
        f.write(j2_template.render(data))

    # generate main.py macros
    logging.info(f"Generating python macros at: {report_dir / 'main.py'}")
    j2_template = Template(macros_template)
    with open(report_dir / "main.py", "w") as f:
        f.write(j2_template.render({'antismash_port' : fileserver_port}))

    # generate custom javascripts
    #script_dir = docs_dir / "scripts"
    #script_dir.mkdir(parents=True, exist_ok=True)
    #logging.info(f"Generating custom site javascripts at: {script_dir / 'site.js'}")
    #with open(script_dir / 'site.js', "w") as f:
    #    f.write(script_js)

    # extend main html
    override_dir = report_dir / 'overrides'
    override_dir.mkdir(exist_ok=True, parents=True)
    logging.info(f"Extends main html: {override_dir / 'main.html'}")
    with open(override_dir / 'main.html', "w") as f:
        f.write(main_html)

    
    # generate symlink
    #asset_path = docs_dir / "assets"
    #asset_path.mkdir(exist_ok=True, parents=True)
    #for r in ['antismash', 'bigscape']:
    #    target_path_raw = report_dir / r
    #    for target_path in target_path_raw.glob("*"):
    #        if any(target_path.name.startswith(keywords) for keywords in ['result', '6']):
    #            if target_path.is_dir():
    #                symlink_path = asset_path / r
    #                if symlink_path.is_symlink():
    #                    symlink_path.unlink()
    #                symlink_path.symlink_to(target_path.resolve())

    # Running fileserver
    fs = subprocess.Popen(["python", "-m", "http.server",'--directory', report_dir, str(fileserver_port)], stderr=subprocess.DEVNULL)
    # dumping file server location
    with open('bgcflow_wrapper.log', "w") as f:
        log_port = {"report_server" : port,
                    "file_server" : fileserver_port,
                    "pid" : fs.pid}
        json.dump(log_port, f, indent=2)
    
    logging.info(f"File-server job id: {fs.pid}")
    try:
        signal.signal(signal.SIGINT, signal_handler)
        mk = subprocess.call(f'(cd {str(report_dir)} && mkdocs serve -a localhost:{port})', shell=True)
        fs.kill()
        #asset_path.rmdir()
    except subprocess.CalledProcessError as e:
        print(e)
        fs.kill()
        #asset_path.rmdir()
    return

def signal_handler(signal, frame):
    print('Thank you for using BGCFlow report!')
    with open('bgcflow_wrapper.log', "r") as f:
        log_port = json.load(f)
        os.kill(log_port['pid'], signal.SIGKILL)
    sys.exit(0)


# template for mkdocs homepage
index_template = """
{% raw %}
# `{{ project().name }}`
Summary report for project `{{ project().name }}`. Generated using [**`BGCFlow v{{ project().bgcflow_version}}`**](https://github.com/NBChub/bgcflow){:target="_blank"}

## Project Description
- {{ project().description }}
- Sample size **{{ project().sample_size }}**
{% endraw %}

## Available reports
{{ rule_table }}

{% raw %}
## References
<font size="2">
{% for i in project().references %}
  - *{{ i }}*
{% endfor %}
</font>
{% endraw %}
"""

# template for index mkdocs
mkdocs_template = {'site_name': 'BGCFlow report',
                   'theme': {'name': 'material',
                             'palette': [{'primary': 'blue'}],
                             'features': ['navigation.tabs', 'toc.integrate'],
                             'custom_dir': 'overrides'
                            },
                   'nav': [{'Home': 'index.md'}],
                   'plugins': ['search',
                               {'mkdocs-jupyter': {'show_input': False,
                                                   'no_input': True,
                                                   'include_source': True,
                                                   'execute': False}},
                               'macros',
                               #{'exclude' : {'glob' : ['docs/assets/*']}}
                              ],
                   #'extra_css': ['https://cdn.datatables.net/1.12.1/css/jquery.dataTables.min.css'],
                   #'extra_javascript': ['https://code.jquery.com/jquery-3.6.0.slim.min.js',
                   #                     'https://cdn.datatables.net/1.12.1/js/jquery.dataTables.min.js',
                   #                     'scripts/site.js'
                   #                    ]
                   'markdown_extensions': ['attr_list'],
                   'extra': {'social' : [{'icon' : 'fontawesome/brands/twitter', 'link' : 'https://twitter.com/NPGMgroup'},
                                         {'icon' : 'fontawesome/brands/github', 'link' : 'https://github.com/NBChub/bgcflow'}
                                        ]}
                  }

# template for mkdocs macros
macros_template = """
import json
import pandas as pd

class Dict2Class(object):
      
    def __init__(self, my_dict):
          
        for key in my_dict:
            setattr(self, key, my_dict[key])
    
    def print_references(self):
        text = ""
        for r in self.references:
          text = "\\n".join([text, f"- {r}"])
        return text
        
    def file_server(self):
        return "{{antismash_port}}"

def define_env(env):
  "Hook function"

  @env.macro
  def project():
      with open("metadata/project_metadata.json", "r") as f:
          project_metadata = json.load(f)
          p = list(project_metadata.values())[0]
          p['name'] = [i for i in project_metadata.keys()][0]
          p = Dict2Class(p)
      return p

  @env.macro
  def read_csv_html(f, as_path):
    df = pd.read_csv(f)
    df = df.loc[:, ["genome_id", "source", "strain"]]
    for i in df.index:
        gid = df.loc[i, 'genome_id']
        df.loc[i, "url"] = f"<a href='{as_path}/{gid}/'>link</a>"
    html = df.to_html(table_id="myTable", 
                      classes=["display"],
                      render_links=True,
                      escape=False).replace('border="1"','').replace('dataframe ', '')
    return html
"""

# template for custom js
script_js = """
$(document).ready(function() {
    $('table.display').DataTable();
} );
"""

# template for html overrides
main_html = """
{% extends "base.html" %}

{% block content %}
{% if page.nb_url %}
    <a href="{{ page.nb_url }}" title="Download Notebook" class="md-content__button md-icon">
        {% include ".icons/material/download.svg" %}
    </a>
{% endif %}

{{ super() }}
{% endblock content %}
"""
