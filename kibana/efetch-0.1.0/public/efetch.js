define(function (require) {
    require('plugins/efetch/efetch_controller');

    // The provider function, which must return our new visualization type
    function EfetchProvider(Private) {
        var TemplateVisType = Private(require('ui/template_vis_type/TemplateVisType'));
        // Include the Schemas class, which will be used to define schemas
        var Schemas = Private(require('ui/Vis/Schemas'));

        // Describe our visualization
        return new TemplateVisType({
            name: 'Efetch', // The internal id of the visualization (must be unique)
            title: 'Efetch', // The title of the visualization, shown to the user
            description: 'Efetch visualization', // The description of this vis
            icon: 'fa-balance-scale', // The font awesome icon of this visualization
            template: require('plugins/efetch/efetch.html'), // The template, that will be rendered for this visualization
            // Define the aggregation your visualization accepts
            params: {
                defaults: {
                    efetchURL: 'http://localhost:8080/plugins/',
                    efetchPlugin: ''
                },
                editor: require('plugins/efetch/efetch_vis_params.html')
            }
        });
    }

    require('ui/registry/vis_types').register(EfetchProvider);

    return EfetchProvider;
});
