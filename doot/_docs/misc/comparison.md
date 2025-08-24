# Comparing Task Runners

## Python-Based
### [Scons](https://scons.org/documentation.html)

[Scons Cookbook](https://scons-cookbook.readthedocs.io/en/latest/)

#### Pros
- python
- order independent

#### Cons
- documentation
- not explicit

### [Toil](https://toil.ucsc-cgl.org/)
[Toil Github](https://github.com/DataBiosphere/toil)

#### Concepts
- leader : decides jobs by traversing job graph
- job store : handles files shared between components, maintains state
- worker : temporary processes, can run on to successors
- batch system : schedules jobs
- node provisioner : creates worker nodes
- stats and logger :

- jobs : atomic unit of work
- workflow : extends job
- jobDescription : metadata

#### Pros
- uses cwl, wdl, python

#### Cons

#### Example
```python
from toil.common import Toil
from toil.job import Job

def helloWorld(message, memory="1G", cores=1, disk="1G"):
    return f"Hello, world!, here's a message: {message}"

if __name__ == "__main__":
    parser = Job.Runner.getDefaultArgumentParser()
    options = parser.parse_args()
    options.clean = "always"
    with Toil(options) as toil:
        output = toil.start(Job.wrapFn(helloWorld, "You did it!"))
    print(output)

```

### [Scrapy](https://scrapy.org/)

#### Concepts
- spiders
- middleware
- pipeline
- runner
- contracts

#### Dataflow
1) The Engine gets the initial Requests to crawl from the Spider.
2) The Engine schedules the Requests in the Scheduler and asks for the next Requests to crawl.
3) The Scheduler returns the next Requests to the Engine.
4) process_request through downloader middlewares,
5) download.
6) process_response through downloader middlewares.
7) process_spider_input through spider middlewares.
8) process_spider_output of new Requests and scraped items.
9) The Engine sends processed items to Item Pipelines, and send processed Requests to the Scheduler and asks for possible next Requests to crawl.
10) The process repeats (from step 3) until there are no more requests from the Scheduler.

#### Pros
- non-blocking,
- modular

#### Cons
- overrules logging

### [Twisted](https://docs.twisted.org/en/stable/index.html)

#### Pros
#### Cons
### [SnakeMake](https://snakemake.readthedocs.io/en/stable/)

#### Concepts

#### Pros
- reproducible
- linter
- modular
- auto install of dependencies
- tool wrappers
- cluster execution
- tabular config
- reports
- generates unit tests
- handover to other task runners

#### Cons
- dsl, uncertain where python ends and snakemake begins
- top down

#### Example
```snakemake
rule bwa_map:
    input:
        "data/genome.fa",
        "data/samples/A.fastq"
    output:
        "mapped_reads/A.bam"
    shell:
        "bwa mem {input} | samtools view -Sb - > {output}"

```

### [Luigi](https://luigi.readthedocs.io/en/stable/design_and_limitations.html)

#### Concepts
Target         - has .exists(), possible .open
Task           - .run(), .output(), .requires()
Parameter      -
Events         -
Event Handlers -

#### Pros
- Straightforward command-line integration.
- As little boilerplate as possible.
- Focus on job scheduling and dependency resolution.
- A file system abstraction where code doesn’t have to care about where files are located.
- Atomic file system operations through this abstraction. If a task crashes it won’t lead to a broken state.
- The dependencies are decentralized. No big config file in XML.
- A web server that renders the dependency graph and does locking, etc for free.
- Trivial to extend with new file systems, file formats, and job types.
- Date algebra included.
- Lots of unit tests of the most basic stuff.

#### Cons
- Its focus is on batch processing so it’s probably less useful for near real-time pipelines or continuously running processes.
- The assumption is that each task is a sizable chunk of work. While you can probably schedule a few thousand jobs, it’s not meant to scale beyond tens of thousands.
- Luigi does not support distribution of execution. When you have workers running thousands of jobs daily, this starts to matter, because the worker nodes get overloaded. There are some ways to mitigate this (trigger from many nodes, use resources), but none of them are ideal.
- Luigi does not come with built-in triggering, and you still need to rely on something like crontab to trigger workflows periodically.

#### Example
```python
  import luigi

  class MyTask(luigi.Task):
      param = luigi.Parameter(default=42)

      def requires(self) -> Task|list[Task]:
          return SomeOtherTask(self.param)

      def run(self):
          with self.output().open('w'):
              ...

      def output(self):
          return luigi.LocalTarget("/temp/foo/bar-%s.txt" % self.param)

@luigi.Task.event_handler(luidi.Event.SUCCESS)
def celebrate_success(task):
    ...
```

### [Doit](https://pydoit.org/contents.html)

#### Pros
- just python

#### Cons
- relies on raw dicts

#### Example
```python
  def task_do_something():
      # Setup code here

      # Task Spec:
      return {
          'actions'  : [...],
          'file_dep' : [...],
          'targets'  : [...],
          }
```

### [Invoke](https://www.pyinvoke.org/)
## Javascript-Based

### [Gulp](https://gulpjs.com/)

#### Concepts
- gulpfile
- tasks : async functions
- public tasks
- private tasks

#### Pros
- combinator based

#### Cons
- javascript

#### Example
```javascript
function defaultTask(cb){
    // do stuff
    cb();
}

exports.default = defaulTask
```

### [Grunt](https://gruntjs.com/)

#### Concepts
- package.json
- gruntfile
- alias tasks
- multi tasks
- basic tasks
- custom tasks

#### Pros
- plugins

#### Cons
- javascript

```javascript
 module.exports = function(grunt) {

  // Project configuration.
  grunt.initConfig({
    pkg: grunt.file.readJSON('package.json'),
    uglify: {
      options: {
        banner: '/*! <%= pkg.name %> <%= grunt.template.today("yyyy-mm-dd") %> */\n'
      },
      build: {
        src: 'src/<%= pkg.name %>.js',
        dest: 'build/<%= pkg.name %>.min.js'
      }
    }
  });

  // Load the plugin that provides the "uglify" task.
  grunt.loadNpmTasks('grunt-contrib-uglify');

  // Default task(s).
  grunt.registerTask('default', ['uglify']);

};
```

## Go-Based
### [Task](https://taskfile.dev/)
## Rust-Based
### [Just](https://just.systems/man/en/)
## Toml Based

### [Mise](https://mise.jdx.dev/tasks/toml-tasks.html)

### [Cargo](https://doc.rust-lang.org/cargo/)

#### Pros

#### Cons

## XML Based
### [Maven](https://maven.apache.org/)

#### Pros

#### Cons

### [Ant](https://ant.apache.org/manual/index.html)

#### Concepts

#### Pros
- stdlib

#### Cons
- java
- xml

## Custom DSLs
### [Ansible](https://www.redhat.com/en/ansible-collaborative)

#### Pros

#### Cons

### [CMake](https://cmake.org/documentation/)

#### Pros

#### Cons

### [Collective Knowledge](https://cknowledge.io/docs/)

#### Pros

#### Cons

### [Common Workflow Language](https://www.commonwl.org/)

#### Pros

#### Cons
- yaml

#### Example
```cwl
cwlVersion: v1.0
class: CommandLineTool
baseCommand: echo
stdout: output.txt
inputs:
  message:
    type: string
    inputBinding:
      position: 1
outputs:
  output:
    type: stdout

```

### [Gradle](https://gradle.org/)

#### Concepts
- settings script
- build script
- project
- subproject
- actionable tasks
- lifecycle tasks
- plugins
- artifact
- capability
- component
- configuration

#### Pros
- plugins
- daemon

#### Cons
- groovy
- gradlew
- unclear syntax
- documentation
- constrained to jvm projects

### [Jenkins](https://www.jenkins.io/doc/)
https://www.jenkins.io/doc/book/pipeline/syntax/

#### Concepts
- jenkinsfile
- pipelines
- sections
- directives
- steps
- agents

#### Pros
- can be declarative or scripted

#### Cons
- groovy

```javascript
pipeline {
    agent any
    options {
        // Timeout counter starts AFTER agent is allocated
        timeout(time: 1, unit: 'SECONDS')
    }
    stages {
        stage('Example') {
            steps {
                echo 'Hello World'
            }
        }
    }
}
```

### [kubernetes](https://kubernetes.io/docs/home/)

#### Concepts
#### Pros
#### Cons
### [OPA](https://www.openpolicyagent.org/)

#### Concepts
- permissions
- agents
- roles
- policy
- rules

#### Pros

#### Cons
- rego

### [Make](https://www.gnu.org/software/make/manual/make.html)

#### Pros
- rule based

#### Cons
- esoteric
- relies on whitespace
- complex var expansion

#### Example
```make
objects = main.o kbd.o command.o display.o \
          insert.o search.o files.o utils.o

edit : $(objects)
        cc -o edit $(objects)
main.o : main.c defs.h
        cc -c main.c
kbd.o : kbd.c defs.h command.h
        cc -c kbd.c
command.o : command.c defs.h command.h
        cc -c command.c
display.o : display.c defs.h buffer.h
        cc -c display.c
insert.o : insert.c defs.h buffer.h
        cc -c insert.c
search.o : search.c defs.h buffer.h
        cc -c search.c
files.o : files.c defs.h buffer.h command.h
        cc -c files.c
utils.o : utils.c defs.h
        cc -c utils.c
clean :
        rm edit $(objects)
```

### [Meson](https://mesonbuild.com/)

#### Pros

#### Cons

### [Nix](https://nixos.org/learn)

#### Concepts
- creates and composes file derivations

#### Pros

#### Cons

### [Rake](https://docs.seattlerb.org/rake/)

#### Pros

#### Cons

### [WDL](https://docs.openwdl.org/en/latest/)

https://github.com/openwdl/wdl
https://openwdl.org/getting-started/
https://github.com/openwdl/wdl/blob/wdl-1.1/SPEC.md

#### Concepts
- workflow
- task
- call
- command
- output

#### Pros

#### Cons

#### Example
```wdl
workflow write_simple_file {
  call write_file
}
task write_file {
  String message
  command { echo ${message} > wdl-helloworld-output.txt }
  output { File test = "wdl-helloworld-output.txt" }
}
```

## [Dagger](https://docs.dagger.io/)

## [TaskCluster](https://docs.taskcluster.net/docs/manual/tasks)

https://taskcluster-taskgraph.readthedocs.io/en/stable/index.html
