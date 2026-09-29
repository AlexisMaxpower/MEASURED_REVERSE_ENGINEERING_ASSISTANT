using System;
using System.IO;
using System.Runtime.InteropServices;
using SolidWorks.Interop.swconst;

namespace Mrea.SolidWorksCadAgent
{
    internal sealed class SolidWorksSession : IDisposable
    {
        private dynamic _app;
        private dynamic _model;
        private readonly bool _launchedByAgent;
        private bool _disposed;

        private SolidWorksSession(dynamic app, dynamic model, bool launchedByAgent)
        {
            _app = app;
            _model = model;
            _launchedByAgent = launchedByAgent;
        }

        public dynamic App { get { return _app; } }
        public dynamic Model { get { return _model; } }

        public static SolidWorksSession Open(AgentRequest request)
        {
            dynamic app = null;
            var launched = false;

            if (request.attach_to_running)
            {
                try
                {
                    app = Marshal.GetActiveObject("SldWorks.Application");
                }
                catch (COMException)
                {
                    app = null;
                }
            }

            if (app == null && request.allow_launch)
            {
                var progId = Type.GetTypeFromProgID("SldWorks.Application", throwOnError: false);
                if (progId == null)
                    throw new InvalidOperationException("SOLIDWORKS COM ProgID SldWorks.Application is not registered.");
                app = Activator.CreateInstance(progId);
                launched = true;
                app.Visible = true;
                try { app.UserControl = true; } catch { }
            }

            if (app == null)
                throw new InvalidOperationException("SOLIDWORKS is not running and allow_launch=false.");

            var template = ResolvePartTemplate(app, request.part_template_path);
            dynamic model = app.NewDocument(template, (int)swDwgPaperSizes_e.swDwgPaperAsize, 0.0, 0.0);
            if (model == null)
                throw new InvalidOperationException("SOLIDWORKS failed to create a new part document from template: " + template);

            SelectFrontPlaneWithoutLocalizedName(app, model);
            dynamic sketchManager = model.SketchManager;
            sketchManager.InsertSketch(true);
            if (sketchManager.ActiveSketch == null)
                throw new InvalidOperationException("SOLIDWORKS did not enter a FRONT-plane sketch.");

            return new SolidWorksSession(app, model, launched);
        }

        private static string ResolvePartTemplate(dynamic app, string requested)
        {
            if (!string.IsNullOrWhiteSpace(requested))
            {
                var explicitPath = Path.GetFullPath(requested);
                if (!File.Exists(explicitPath))
                    throw new FileNotFoundException("Requested SOLIDWORKS part template does not exist.", explicitPath);
                return explicitPath;
            }

            string template = app.GetUserPreferenceStringValue((int)swUserPreferenceStringValue_e.swDefaultTemplatePart);
            if (string.IsNullOrWhiteSpace(template) || !File.Exists(template))
                throw new InvalidOperationException(
                    "SOLIDWORKS default part template is not configured. Pass part_template_path explicitly.");
            return template;
        }

        private static void SelectFrontPlaneWithoutLocalizedName(dynamic app, dynamic model)
        {
            dynamic math = app.GetMathUtility();
            dynamic canonicalNormal = math.CreateVector(new double[] { 0.0, 0.0, 1.0 });
            dynamic canonicalOrigin = math.CreatePoint(new double[] { 0.0, 0.0, 0.0 });

            dynamic bestFeature = null;
            double bestScore = double.NegativeInfinity;
            dynamic feature = model.FirstFeature();
            while (feature != null)
            {
                string typeName = null;
                try { typeName = feature.GetTypeName2(); } catch { }
                if (string.Equals(typeName, "RefPlane", StringComparison.OrdinalIgnoreCase))
                {
                    try
                    {
                        dynamic refPlane = feature.GetSpecificFeature2();
                        dynamic transform = refPlane.Transform;
                        dynamic normal = canonicalNormal.MultiplyTransform(transform);
                        dynamic origin = canonicalOrigin.MultiplyTransform(transform);
                        var n = ToDoubleArray(normal.ArrayData);
                        var o = ToDoubleArray(origin.ArrayData);
                        if (n.Length >= 3 && o.Length >= 3)
                        {
                            var normalDotZ = n[2];
                            var originDistance = Math.Sqrt(o[0] * o[0] + o[1] * o[1] + o[2] * o[2]);
                            // SOLIDWORKS defines canonical RefPlane orientation as the system Front Plane.
                            // Prefer +Z normal and a plane through the origin, without localized feature names.
                            var score = normalDotZ * 1000.0 - originDistance;
                            if (score > bestScore)
                            {
                                bestScore = score;
                                bestFeature = feature;
                            }
                        }
                    }
                    catch
                    {
                        // Keep traversing: a user plane must not hide a usable system Front Plane.
                    }
                }
                feature = feature.GetNextFeature();
            }

            if (bestFeature == null || bestScore < 999.0)
                throw new InvalidOperationException("Could not identify the system FRONT reference plane from reference-plane transforms.");

            model.ClearSelection2(true);
            if (!bestFeature.Select2(false, 0))
                throw new InvalidOperationException("Failed to select the system FRONT reference plane.");
        }

        private static double[] ToDoubleArray(object raw)
        {
            var array = raw as Array;
            if (array == null)
                return new double[0];
            var result = new double[array.Length];
            for (var i = 0; i < array.Length; i++)
                result[i] = Convert.ToDouble(array.GetValue(i));
            return result;
        }

        public void Dispose()
        {
            if (_disposed)
                return;
            _disposed = true;

            try
            {
                if (_model != null)
                {
                    string title = null;
                    try { title = _model.GetTitle(); } catch { }
                    try
                    {
                        dynamic sketchManager = _model.SketchManager;
                        if (sketchManager != null && sketchManager.ActiveSketch != null)
                            sketchManager.InsertSketch(true);
                    }
                    catch { }

                    if (!string.IsNullOrWhiteSpace(title))
                    {
                        try { _app.CloseDoc(title); } catch { }
                    }
                }
            }
            finally
            {
                ReleaseCom(_model);
                _model = null;
                if (_launchedByAgent)
                {
                    // UserControl is enabled when launched; never terminate the whole user session here.
                }
                ReleaseCom(_app);
                _app = null;
            }
        }

        private static void ReleaseCom(object value)
        {
            if (value == null || !Marshal.IsComObject(value))
                return;
            try { Marshal.FinalReleaseComObject(value); } catch { }
        }
    }
}
