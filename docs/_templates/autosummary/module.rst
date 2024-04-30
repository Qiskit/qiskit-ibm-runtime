{#
   This is the same as
   https://github.com/sphinx-doc/sphinx/blob/master/sphinx/ext/autosummary/templates/autosummary/module.rst
   other than removing the first line which automatically sets the `h1` to
   full import path. We should instead use the header from the module file itself.
-#}

.. automodule:: {{ fullname }}

   {% block attributes %}
   {% if attributes %}
   .. rubric:: {{ _('Module Attributes') }}

   .. autosummary::
   {% for item in attributes %}
      {{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}

   {% block functions %}
   {% if functions %}
   .. rubric:: {{ _('Functions') }}

   .. autosummary::
   {% for item in functions %}
      {{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}

   {% block classes %}
   {% if classes %}
   .. rubric:: {{ _('Classes') }}

   .. autosummary::
   {% for item in classes %}
      {{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}

   {% block exceptions %}
   {% if exceptions %}
   .. rubric:: {{ _('Exceptions') }}

   .. autosummary::
   {% for item in exceptions %}
      {{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}

{% block modules %}
{% if modules %}
.. rubric:: Modules

.. autosummary::
   :toctree:
   :recursive:
{% for item in modules %}
   {{ item }}
{%- endfor %}
{% endif %}
{% endblock %}