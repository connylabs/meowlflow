local kpm = import "kpm.libjsonnet";

function(
  params={}
)

kpm.package({
   package: {
      name: "mietright/meowlflow",
      expander: "jinja2",
      author: "Conny ML",
      version: "0.0.1-1",
      description: "meowlflow",
      license: "Apache 2.0",
    },

    variables: {
      appname: "meowlflow",
      namespace: 'default',
      image: "image.conny.dev/conny/meowlflow:v0.0.1",
      svc_type: "LoadBalancer",
    },

    resources: [
      {
        file: "meowlflow-dp.yaml",
        template: (importstr "templates/meowlflow-dp.yaml"),
        name: "meowlflow",
        type: "deployment",
      },

      {
        file: "meowlflow-svc.yaml",
        template: (importstr "templates/meowlflow-svc.yaml"),
        name: "meowlflow",
        type: "service",
      }
      ],


    deploy: [
      {
        name: "$self",
      },
    ],


  }, params)
